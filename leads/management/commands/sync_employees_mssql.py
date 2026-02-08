import pyodbc
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from leads.models import Employee, SyncSettings


class Command(BaseCommand):
    help = "Синхронизация сотрудников из MSSQL в Employee (без трогания Company)"

    MSSQL_CONN_STR = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=ink-sqlsrv-dwh;"
        "DATABASE=DWH;"
        "UID=info_conferences;"
        "PWD={lzxV9TF);*jpucr9BkXb};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )

    def handle(self, *args, **options):
        settings = SyncSettings.get_settings()
        now = timezone.localtime(timezone.now())

        # 1) Интервал (по умолчанию 24 часа)
        if settings.last_sync:
            hours_passed = (now - timezone.localtime(settings.last_sync)).total_seconds() / 3600
            if hours_passed < settings.interval_hours:
                self.stdout.write(self.style.WARNING(
                    f"Рано: прошло {hours_passed:.1f}h из {settings.interval_hours}h"
                ))
                return

        # 2) Ночной режим 00:00–06:00 (если включён)
        if settings.night_only:
            h = now.hour
            if not (settings.night_start_hour <= h < settings.night_end_hour):
                self.stdout.write(self.style.WARNING(
                    f"Ночной режим: {settings.night_start_hour:02d}:00–{settings.night_end_hour:02d}:00, сейчас {h:02d}:xx"
                ))
                return

        conn = None
        try:
            conn = pyodbc.connect(self.MSSQL_CONN_STR)
            cursor = conn.cursor()

            cursor.execute("""
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
                WHERE u.[sAMAccountName] IS NOT NULL
                  AND u.[mail] IS NOT NULL
                  AND u.[company] IS NOT NULL
                  AND u.[department] IS NOT NULL
                  AND u.[jobTitle] IS NOT NULL
            """)

            rows = cursor.fetchall()

            active_guids = set()
            created_count = 0
            updated_count = 0

            with transaction.atomic():
                for row in rows:
                    guid = str(row[0]).strip()
                    active_guids.add(guid)

                    full_name = (row[1].strip() if row[1] else "")[:100]
                    parts = full_name.split()
                    last_name = (parts[0] if parts else "")[:50]
                    first_name = (parts[1] if len(parts) > 1 else "")[:50]
                    patronymic_name = (" ".join(parts[2:]) if len(parts) > 2 else "")[:50]

                    defaults = {
                        "full_name": full_name,
                        "last_name": last_name,
                        "first_name": first_name,
                        "patronymic_name": patronymic_name,
                        "sam_account_name": (row[2] or "").strip()[:100],
                        "email": (row[3] or "").strip()[:254],
                        "company_text": (row[4] or "").strip()[:255],  # ✅ просто текст
                        "department": (row[5] or "").strip()[:150],
                        "job_title": (row[6] or "").strip()[:150],
                        "sync_status": "active",
                        "deleted_at": None,
                    }

                    emp, created = Employee.objects.update_or_create(
                        guid=guid,
                        defaults=defaults
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                # 3) GUID которых больше нет в MSSQL — помечаем deleted
                qs = Employee.objects.exclude(guid__in=active_guids).exclude(sync_status="deleted")
                deleted_count = qs.update(sync_status="deleted", deleted_at=now)

                # 4) last_sync
                settings.last_sync = now
                settings.save(update_fields=["last_sync"])

            self.stdout.write(self.style.SUCCESS(
                f"OK: создано={created_count}, обновлено={updated_count}, помечено deleted={deleted_count}"
            ))

        except pyodbc.Error as e:
            self.stdout.write(self.style.ERROR(f"MSSQL error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
        finally:
            if conn:
                conn.close()
