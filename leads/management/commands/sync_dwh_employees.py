from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.utils import timezone

from leads.models import EmployeeDwh

SQL = """
SELECT
    i.[GUID_NSI],
    i.[name],
    u.[sAMAccountName],
    u.[mail],
    u.[company],
    u.[department],
    u.[jobTitle]
FROM [DWH].[dbo].[Individuals] i
LEFT JOIN [DWH].[ad].[Users] u ON i.[Login] = u.[sAMAccountName]
WHERE
    u.[sAMAccountName] IS NOT NULL
    AND u.[mail] IS NOT NULL
    AND u.[company] IS NOT NULL
    AND u.[department] IS NOT NULL
    AND u.[jobTitle] IS NOT NULL
"""

class Command(BaseCommand):
    help = "Sync employees from MS SQL DWH into Django table (upsert + soft-delete)"

    log_path = Path(settings.BASE_DIR) / "logs" / "sync_dwh_employees.log"

    def write_sync_log(self, lines):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def format_employee(self, employee):
        return (
            f"guid={employee.guid_nsi} | "
            f"name={employee.full_name} | "
            f"sam={employee.samaccountname} | "
            f"mail={employee.mail} | "
            f"company={employee.company} | "
            f"department={employee.department} | "
            f"job_title={employee.job_title} | "
            f"status={employee.status}"
        )

    def handle(self, *args, **options):
        now = timezone.now()
        log_lines = [
            f"sync_dwh_employees started_at={now.isoformat()}",
            "source=[DWH].[dbo].[Individuals] LEFT JOIN [DWH].[ad].[Users]",
            "filter=sAMAccountName/mail/company/department/jobTitle IS NOT NULL",
            "",
        ]

        # 1) fetch from MSSQL
        try:
            with connections["dwh"].cursor() as cursor:
                cursor.execute(SQL)
                rows = cursor.fetchall()
        except Exception as exc:
            failed_at = timezone.now()
            log_lines.extend([
                f"status=FAILED",
                f"failed_at={failed_at.isoformat()}",
                f"duration_seconds={(failed_at - now).total_seconds():.3f}",
                f"error={type(exc).__name__}: {exc}",
            ])
            self.write_sync_log(log_lines)
            raise

        log_lines.append(f"fetched_from_dwh={len(rows)}")

        # нормализуем в dict по GUID
        incoming = {}
        for guid_nsi, name, sam, mail, company, dept, title in rows:
            if not guid_nsi:
                continue
            incoming[str(guid_nsi).lower()] = {
                "guid_nsi": guid_nsi,
                "full_name": (name or "").strip(),
                "samaccountname": (sam or "").strip(),
                "mail": (mail or "").strip(),
                "company": (company or "").strip(),
                "department": (dept or "").strip(),
                "job_title": (title or "").strip(),
            }

        guids = list(incoming.keys())

        # 2) load existing from Postgres by GUID
        existing = {
            str(e.guid_nsi).lower(): e
            for e in EmployeeDwh.objects.filter(guid_nsi__in=[incoming[g]["guid_nsi"] for g in guids]).only(
                "id", "guid_nsi", "full_name", "samaccountname", "mail",
                "company", "department", "job_title", "status", "source_last_seen_at", "deleted_at"
            )
        }

        to_create = []
        to_update = []
        changed_or_reactivated = []

        for guid_key, data in incoming.items():
            obj = existing.get(guid_key)
            if obj is None:
                to_create.append(EmployeeDwh(
                    guid_nsi=data["guid_nsi"],
                    full_name=data["full_name"],
                    samaccountname=data["samaccountname"],
                    mail=data["mail"],
                    company=data["company"],
                    department=data["department"],
                    job_title=data["job_title"],
                    status=EmployeeDwh.Status.ACTIVE,
                    source_last_seen_at=now,
                    deleted_at=None,
                ))
            else:
                changed = False
                data_changed = False

                # upsert fields
                for field in ["full_name","samaccountname","mail","company","department","job_title"]:
                    new_val = data[field]
                    if getattr(obj, field) != new_val:
                        setattr(obj, field, new_val)
                        changed = True
                        data_changed = True

                # если раньше был deleted — вернуть в active
                if obj.status != EmployeeDwh.Status.ACTIVE:
                    obj.status = EmployeeDwh.Status.ACTIVE
                    obj.deleted_at = None
                    changed = True
                    data_changed = True

                if obj.source_last_seen_at != now:
                    obj.source_last_seen_at = now
                    changed = True

                if data_changed:
                    changed_or_reactivated.append(obj)

                if changed:
                    to_update.append(obj)

        # 3) mark missing as deleted (soft delete)
        # NOTE: считаем "отсутствующих" среди тех, кто был активен и кого не видели сейчас
        with transaction.atomic():
            seen_guids = [incoming[g]["guid_nsi"] for g in guids]
            to_delete = list(
                EmployeeDwh.objects.filter(
                    status=EmployeeDwh.Status.ACTIVE
                ).exclude(
                    guid_nsi__in=seen_guids
                ).only(
                    "id", "guid_nsi", "full_name", "samaccountname", "mail",
                    "company", "department", "job_title", "status"
                )
            )

            if to_create:
                EmployeeDwh.objects.bulk_create(to_create, batch_size=1000)

            if to_update:
                EmployeeDwh.objects.bulk_update(
                    to_update,
                    ["full_name","samaccountname","mail","company","department","job_title","status","source_last_seen_at","deleted_at"],
                    batch_size=1000
                )

            # помечаем тех, кого не видели в источнике в этом прогоне
            deleted_count = EmployeeDwh.objects.filter(
                status=EmployeeDwh.Status.ACTIVE
            ).exclude(
                guid_nsi__in=seen_guids
            ).update(
                status=EmployeeDwh.Status.DELETED,
                deleted_at=now
            )

        log_lines.extend([
            f"incoming_unique_guids={len(incoming)}",
            f"created={len(to_create)}",
            f"updated_last_seen_or_data={len(to_update)}",
            f"changed_or_reactivated={len(changed_or_reactivated)}",
            f"soft_deleted={deleted_count}",
            "",
            "CREATED:",
        ])
        if to_create:
            log_lines.extend(f"  {self.format_employee(e)}" for e in to_create)
        else:
            log_lines.append("  none")

        log_lines.append("")
        log_lines.append("CHANGED_OR_REACTIVATED:")
        if changed_or_reactivated:
            log_lines.extend(f"  {self.format_employee(e)}" for e in changed_or_reactivated)
        else:
            log_lines.append("  none")

        log_lines.append("")
        log_lines.append("SOFT_DELETED:")
        if to_delete:
            log_lines.extend(f"  {self.format_employee(e)}" for e in to_delete)
        else:
            log_lines.append("  none")

        finished_at = timezone.now()
        log_lines.extend([
            "",
            f"finished_at={finished_at.isoformat()}",
            f"duration_seconds={(finished_at - now).total_seconds():.3f}",
        ])
        self.write_sync_log(log_lines)

        self.stdout.write(self.style.SUCCESS(
            f"Done. fetched={len(rows)} upsert_create={len(to_create)} upsert_update={len(to_update)} soft_deleted={deleted_count} log={self.log_path}"
        ))
