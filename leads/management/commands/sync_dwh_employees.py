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

    def handle(self, *args, **options):
        now = timezone.now()

        # 1) fetch from MSSQL
        with connections["dwh"].cursor() as cursor:
            cursor.execute(SQL)
            rows = cursor.fetchall()

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

                # upsert fields
                for field in ["full_name","samaccountname","mail","company","department","job_title"]:
                    new_val = data[field]
                    if getattr(obj, field) != new_val:
                        setattr(obj, field, new_val)
                        changed = True

                # если раньше был deleted — вернуть в active
                if obj.status != EmployeeDwh.Status.ACTIVE:
                    obj.status = EmployeeDwh.Status.ACTIVE
                    obj.deleted_at = None
                    changed = True

                if obj.source_last_seen_at != now:
                    obj.source_last_seen_at = now
                    changed = True

                if changed:
                    to_update.append(obj)

        # 3) mark missing as deleted (soft delete)
        # NOTE: считаем "отсутствующих" среди тех, кто был активен и кого не видели сейчас
        with transaction.atomic():
            if to_create:
                EmployeeDwh.objects.bulk_create(to_create, batch_size=1000)

            if to_update:
                EmployeeDwh.objects.bulk_update(
                    to_update,
                    ["full_name","samaccountname","mail","company","department","job_title","status","source_last_seen_at","deleted_at"],
                    batch_size=1000
                )

            # помечаем тех, кого не видели в источнике в этом прогоне
            seen_guids = [incoming[g]["guid_nsi"] for g in guids]
            deleted_count = EmployeeDwh.objects.filter(
                status=EmployeeDwh.Status.ACTIVE
            ).exclude(
                guid_nsi__in=seen_guids
            ).update(
                status=EmployeeDwh.Status.DELETED,
                deleted_at=now
            )

        self.stdout.write(self.style.SUCCESS(
            f"Done. fetched={len(rows)} upsert_create={len(to_create)} upsert_update={len(to_update)} soft_deleted={deleted_count}"
        ))
