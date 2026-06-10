import re
from django.core.management.base import BaseCommand
from django.db import transaction

from leads.models import Lead, EmployeeDwh


def norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def build_fio(lead: Lead) -> str:
    parts = [lead.last_name, lead.first_name, lead.patronymic_name]
    parts = [norm_spaces(p) for p in parts if norm_spaces(p)]
    return " ".join(parts)


def build_fio_initials(lead: Lead) -> str:
    last = norm_spaces(lead.last_name)
    first = norm_spaces(lead.first_name)
    patr = norm_spaces(lead.patronymic_name)

    if not last:
        return ""

    fi = first[0] if first else ""
    pi = patr[0] if patr else ""
    # формат "Фамилия И О" (с пробелами)
    parts = [last]
    if fi:
        parts.append(fi)
    if pi:
        parts.append(pi)
    return " ".join(parts)


class Command(BaseCommand):
    help = "One-time: link existing Leads to EmployeeDwh by FIO rules; unresolved leads keep display_name unchanged."

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

    def handle(self, *args, **options):
        dry = options["dry_run"]
        clear_fio = options["clear_fio"]
        limit = options["limit"]

        qs = Lead.objects.all().order_by("id")
        if limit and limit > 0:
            qs = qs[:limit]

        linked = 0
        unresolved_left_empty = 0
        ambiguous = 0
        not_found = 0
        skipped = 0

        # Предзагрузка сотрудников (ACTIVE+DELETED — чтобы можно было линковать и уволенных, если они были в старых Lead)
        employees = list(EmployeeDwh.objects.all().only("id", "full_name", "guid_nsi"))
        full_map = {}
        init_map = {}

        for e in employees:
            full = norm_spaces(e.full_name).lower()
            if full:
                full_map.setdefault(full, []).append(e)

            # строим "Фамилия И О" из full_name
            parts = norm_spaces(e.full_name).split()
            if len(parts) >= 2:
                last = parts[0]
                fi = parts[1][0] if parts[1] else ""
                pi = parts[2][0] if len(parts) >= 3 and parts[2] else ""
                key = " ".join([p for p in [last, fi, pi] if p]).lower()
                if key:
                    init_map.setdefault(key, []).append(e)

        with transaction.atomic():
            for lead in qs:
                fio = build_fio(lead)
                if not fio:
                    skipped += 1
                    continue

                # если уже есть employees — можно пропустить (или перелинковать). Я пропускаю, чтобы не ломать руками выставленное.
                if lead.employees.exists():
                    skipped += 1
                    continue

                # 1) полное совпадение
                key_full = fio.lower()
                cands = full_map.get(key_full, [])

                # 2) если нет — по инициалам
                if not cands:
                    key_init = build_fio_initials(lead).lower()
                    cands = init_map.get(key_init, [])

                if len(cands) == 1:
                    emp = cands[0]
                    linked += 1
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
                    if not norm_spaces(lead.display_name):
                        unresolved_left_empty += 1

                else:
                    ambiguous += 1
                    if not norm_spaces(lead.display_name):
                        unresolved_left_empty += 1

            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Done. linked={linked}, unresolved_left_empty={unresolved_left_empty}, "
            f"not_found={not_found}, ambiguous={ambiguous}, skipped={skipped}, dry_run={dry}"
        ))
