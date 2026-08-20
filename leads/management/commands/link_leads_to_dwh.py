import csv
import re
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from leads.models import Lead, EmployeeDwh


COMPANY_PREFIX_WORDS = {
    "изп",
    "инк",
    "инкс",
    "ук",
    "гпз",
    "ооо",
    "ао",
}


def norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def norm_key(s: str) -> str:
    value = re.sub(r"[.\u00b7]+", " ", s or "")
    return norm_spaces(value).lower()


def build_fio(lead: Lead) -> str:
    parts = [lead.last_name, lead.first_name, lead.patronymic_name]
    parts = [norm_spaces(p) for p in parts if norm_spaces(p)]
    return " ".join(parts)


def split_person_name(value: str):
    return norm_key(value).split()


def lead_name_parts(lead: Lead):
    return split_person_name(build_fio(lead))


def has_multiple_person_marker(value: str) -> bool:
    return "/" in (value or "")


def person_initials_tail(parts):
    if len(parts) < 3:
        return []

    last_three = parts[-3:]
    if (
        len(last_three[1]) == 1
        and len(last_three[2]) == 1
        and all(p.isalpha() for p in last_three)
    ):
        return last_three

    last_two = parts[-2:]
    if (
        len(last_two[1]) == 2
        and all(p.isalpha() for p in last_two)
    ):
        return last_two

    return []


def has_company_prefix(parts, tail):
    prefix = parts[:len(parts) - len(tail)]
    return bool(prefix) and all(part in COMPANY_PREFIX_WORDS for part in prefix)


def lead_match_parts(lead: Lead):
    fio = build_fio(lead)
    parts = split_person_name(fio)
    if has_multiple_person_marker(fio):
        return parts

    tail = person_initials_tail(parts)
    if tail and has_company_prefix(parts, tail):
        return tail
    return parts


def employee_name_parts(employee: EmployeeDwh):
    return split_person_name(employee.full_name)


def initials_key(parts):
    if len(parts) < 3:
        return ""
    last, first, patronymic = parts[0], parts[1], parts[2]
    if not last or not first or not patronymic:
        return ""
    return " ".join([last, first[0], patronymic[0]])


def lead_initials_key(parts):
    if len(parts) == 3:
        return initials_key(parts)
    if len(parts) == 2 and len(parts[1]) == 2 and parts[1].isalpha():
        return " ".join([parts[0], parts[1][0], parts[1][1]])
    return ""


def last_name_key(parts):
    return parts[0] if parts else ""


def fio_from_parts(parts):
    return " ".join(parts)


def describe_part_diff(label, lead_value, employee_value):
    if not lead_value and not employee_value:
        return ""
    if not lead_value:
        return f"{label}: в Lead пусто, в DWH {employee_value}"
    if not employee_value:
        return f"{label}: в Lead {lead_value}, в DWH пусто"
    if lead_value == employee_value:
        return f"{label}: совпало {lead_value}"
    if len(lead_value) == 1 and employee_value.startswith(lead_value):
        return f"{label}: инициал {lead_value} совпал с {employee_value}"
    if len(employee_value) == 1 and lead_value.startswith(employee_value):
        return f"{label}: Lead {lead_value} совпал с инициалом DWH {employee_value}"
    return f"{label}: Lead {lead_value} != DWH {employee_value}"


def describe_fio_diff(lead_parts, employee):
    employee_parts = employee_name_parts(employee)
    labels = ["фамилия", "имя", "отчество"]
    messages = []
    for index, label in enumerate(labels):
        lead_value = lead_parts[index] if len(lead_parts) > index else ""
        employee_value = employee_parts[index] if len(employee_parts) > index else ""
        message = describe_part_diff(label, lead_value, employee_value)
        if message:
            messages.append(message)
    if len(lead_parts) != len(employee_parts):
        messages.append(f"частей ФИО: Lead {len(lead_parts)}, DWH {len(employee_parts)}")
    return "; ".join(messages)


def format_employee(employee: EmployeeDwh) -> str:
    return (
        f"{employee.full_name} | guid={employee.guid_nsi} | "
        f"sam={employee.samaccountname} | company={employee.company}"
    )


class Command(BaseCommand):
    help = "One-time: link existing Leads to EmployeeDwh by FIO rules; unresolved leads keep display_name unchanged."
    default_report_path = Path(settings.BASE_DIR) / "logs" / "link_leads_to_dwh_report.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write changes, only show stats."
        )
        parser.add_argument(
            "--clear-fio",
            action="store_true",
            help="After successful link, clear Lead first_name/last_name/patronymic_name (optional)."
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process only first N leads (for testing)."
        )
        parser.add_argument(
            "--report-path",
            default=str(self.default_report_path),
            help="CSV report path with linked, ambiguous and not_found rows."
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        clear_fio = options["clear_fio"]
        limit = options["limit"]
        report_path = Path(options["report_path"])

        qs = Lead.objects.select_related("phone_number").prefetch_related("employees", "company").all().order_by("id")
        if limit and limit > 0:
            qs = qs[:limit]

        linked = 0
        unresolved_left_empty = 0
        ambiguous = 0
        not_found = 0
        skipped_existing = 0
        skipped_no_fio = 0
        report_rows = []

        # Предзагрузка сотрудников (ACTIVE+DELETED — чтобы можно было линковать и уволенных, если они были в старых Lead)
        employees = list(EmployeeDwh.objects.all().only(
            "id", "full_name", "guid_nsi", "samaccountname", "company"
        ))
        full_map = defaultdict(list)
        init_map = defaultdict(list)
        last_name_map = defaultdict(list)

        for e in employees:
            parts = employee_name_parts(e)
            full = norm_key(e.full_name)
            if full:
                full_map[full].append(e)

            key = initials_key(parts)
            if key:
                init_map[key].append(e)

            last = last_name_key(parts)
            if last:
                last_name_map[last].append(e)

        with transaction.atomic():
            for lead in qs:
                fio = build_fio(lead)
                lead_parts = lead_match_parts(lead)
                same_last_name_candidates = last_name_map.get(last_name_key(lead_parts), [])
                if not fio:
                    skipped_no_fio += 1
                    report_rows.append(self.build_report_row(
                        lead, "skipped_no_fio", "", [], same_last_name_candidates
                    ))
                    continue

                # если уже есть employees — можно пропустить (или перелинковать). Я пропускаю, чтобы не ломать руками выставленное.
                if lead.employees.exists():
                    skipped_existing += 1
                    report_rows.append(self.build_report_row(
                        lead,
                        "skipped_existing",
                        "already_has_employees",
                        list(lead.employees.all()),
                        same_last_name_candidates,
                    ))
                    continue

                # 1) полное совпадение
                key_full = norm_key(fio_from_parts(lead_parts))
                cands = full_map.get(key_full, [])
                match_rule = "full_name"

                # 2) если нет — по инициалам
                if not cands:
                    key_init = lead_initials_key(lead_parts)
                    cands = init_map.get(key_init, [])
                    match_rule = "initials" if key_init else "no_initials_key"

                if len(cands) == 1:
                    emp = cands[0]
                    linked += 1
                    report_rows.append(self.build_report_row(
                        lead, "linked", match_rule, [emp], same_last_name_candidates
                    ))
                    if not dry:
                        lead.save()  # надо сохранить, чтобы M2M можно было поставить (на всякий)
                        lead.employees.add(emp)

                        # опционально очищаем ФИО в Lead
                        if clear_fio:
                            lead.first_name = ""
                            lead.last_name = ""
                            lead.patronymic_name = ""
                            lead.save(update_fields=["first_name", "last_name", "patronymic_name"])

                elif len(cands) == 0:
                    not_found += 1
                    report_rows.append(self.build_report_row(
                        lead, "not_found", match_rule, [], same_last_name_candidates
                    ))
                    if not norm_spaces(lead.display_name):
                        unresolved_left_empty += 1

                else:
                    ambiguous += 1
                    report_rows.append(self.build_report_row(
                        lead, "ambiguous", match_rule, cands, same_last_name_candidates
                    ))
                    if not norm_spaces(lead.display_name):
                        unresolved_left_empty += 1

            if dry:
                transaction.set_rollback(True)

        self.write_report(report_path, report_rows)

        self.stdout.write(self.style.SUCCESS(
            f"Done. linked={linked}, unresolved_left_empty={unresolved_left_empty}, "
            f"not_found={not_found}, ambiguous={ambiguous}, "
            f"skipped_existing={skipped_existing}, skipped_no_fio={skipped_no_fio}, "
            f"dry_run={dry}, report={report_path}"
        ))

    def build_report_row(self, lead, status, match_rule, candidates, same_last_name_candidates):
        lead_parts = lead_match_parts(lead)
        lead_initials = lead_initials_key(lead_parts)
        comparison_candidates = candidates or same_last_name_candidates
        old_companies = ", ".join(c.name for c in lead.company.all())
        return {
            "lead_id": lead.id,
            "phone_number": getattr(lead.phone_number, "name", ""),
            "mac_address": lead.mac_address,
            "lead_fio": build_fio(lead),
            "lead_normalized_fio": norm_key(build_fio(lead)),
            "lead_initials_key": lead_initials,
            "display_name": lead.display_name,
            "old_companies": old_companies,
            "status": status,
            "match_rule": match_rule,
            "match_reason": self.build_match_reason(status, match_rule, candidates, same_last_name_candidates),
            "candidates_count": len(candidates),
            "candidates": " || ".join(format_employee(e) for e in candidates),
            "same_last_name_count": len(same_last_name_candidates),
            "same_last_name_candidates": " || ".join(format_employee(e) for e in same_last_name_candidates[:20]),
            "fio_differences": " || ".join(
                f"{e.full_name}: {describe_fio_diff(lead_parts, e)}"
                for e in comparison_candidates[:20]
            ),
        }

    def build_match_reason(self, status, match_rule, candidates, same_last_name_candidates):
        if status == "linked":
            if match_rule == "full_name":
                return "Однозначное полное совпадение ФИО."
            if match_rule == "initials":
                return "Однозначное совпадение по фамилии и первым буквам имени/отчества."
        if status == "ambiguous":
            return "Найдено несколько кандидатов по правилу матчинга, автоматическая привязка пропущена."
        if status == "not_found":
            if same_last_name_candidates:
                return "Точного совпадения нет, но есть сотрудники с такой же фамилией; проверьте различия ФИО."
            return "Совпадений и сотрудников с такой же фамилией в DWH не найдено."
        if status == "skipped_existing":
            return "Запись уже была привязана к сотруднику, ручную привязку не трогаем."
        if status == "skipped_no_fio":
            return "В Lead нет ФИО для матчинга."
        return ""

    def write_report(self, report_path, rows):
        report_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "lead_id",
            "phone_number",
            "mac_address",
            "lead_fio",
            "lead_normalized_fio",
            "lead_initials_key",
            "display_name",
            "old_companies",
            "status",
            "match_rule",
            "match_reason",
            "candidates_count",
            "candidates",
            "same_last_name_count",
            "same_last_name_candidates",
            "fio_differences",
        ]
        with report_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
