from django.core.management.base import BaseCommand
from django.db import connections, transaction

from .models import Lead, Company, Apparats, Number, Atc, User, EmployeeDwh

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
    help = "Sync employees from MS SQL DWH into Django table"

    def handle(self, *args, **options):
        with connections["dwh"].cursor() as cursor:
            cursor.execute(SQL)
            rows = cursor.fetchall()

        # row: (guid, name, sam, mail, company, dept, title)
        existing = {
            e.guid_nsi: e
            for e in EmployeeDwh.objects.all().only(
                "id", "guid_nsi", "full_name", "samaccountname", "mail", "company", "department", "job_title"
            )
        }

        to_create = []
        to_update = []

        for guid_nsi, name, sam, mail, company, dept, title in rows:
            guid_nsi = str(guid_nsi)  # иногда драйвер отдаёт UUID/str по-разному

            obj = existing.get(guid_nsi)
            if obj is None:
                to_create.append(EmployeeDwh(
                    guid_nsi=guid_nsi,
                    full_name=name,
                    samaccountname=sam,
                    mail=mail,
                    company=company,
                    department=dept,
                    job_title=title,
                ))
            else:
                changed = False
                if obj.full_name != name: obj.full_name = name; changed = True
                if obj.samaccountname != sam: obj.samaccountname = sam; changed = True
                if obj.mail != mail: obj.mail = mail; changed = True
                if obj.company != company: obj.company = company; changed = True
                if obj.department != dept: obj.department = dept; changed = True
                if obj.job_title != title: obj.job_title = title; changed = True

                if changed:
                    to_update.append(obj)

        with transaction.atomic():
            if to_create:
                EmployeeDwh.objects.bulk_create(to_create, batch_size=1000)
            if to_update:
                EmployeeDwh.objects.bulk_update(
                    to_update,
                    ["full_name", "samaccountname", "mail", "company", "department", "job_title"],
                    batch_size=1000
                )

        self.stdout.write(self.style.SUCCESS(
            f"Done. fetched={len(rows)} created={len(to_create)} updated={len(to_update)}"
        ))
