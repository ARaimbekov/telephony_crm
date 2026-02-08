import pyodbc
from django.core.management.base import BaseCommand
from django.utils import timezone
from leads.models import Employee, Company, SyncSettings

class Command(BaseCommand):
    help = 'Синхронизация сотрудников из MSSQL в модель Employee'

    def handle(self, *args, **options):
        settings = SyncSettings.get_settings()
        now = timezone.now()

        # Проверка, пора ли синхронизировать
        if settings.last_sync:
            hours_passed = (now - settings.last_sync).total_seconds() / 3600
            if hours_passed < settings.interval_hours:
                self.stdout.write(self.style.WARNING(
                    f'Ещё рано: прошло {hours_passed:.1f} часов из {settings.interval_hours}'
                ))
                return

        if settings.night_only and not (0 <= now.hour < 6):
            self.stdout.write(self.style.WARNING('Синхронизация только ночью (00:00–06:00)'))
            return

        # Строка подключения (твои реальные данные)
        conn_str = (
            'DRIVER={ODBC Driver 18 for SQL Server};'
            'SERVER=ink-sqlsrv-dwh;'
            'DATABASE=DWH;'
            'UID=info_conferences;'
            'PWD=lzxV9TF);*jpucr9BkXb;'
            'TrustServerCertificate=yes;'
        )

        try:
            conn = pyodbc.connect(conn_str)
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

            for row in rows:
                guid = str(row[0]).strip()
                active_guids.add(guid)

                full_name = row[1].strip()
                name_parts = full_name.split()
                last_name = name_parts[0] if name_parts else ''
                first_name = name_parts[1] if len(name_parts) > 1 else ''
                patronymic_name = ' '.join(name_parts[2:]) if len(name_parts) > 2 else ''

                company_name = row[4].strip()
                company, _ = Company.objects.get_or_create(name=company_name)

                defaults = {
                    'full_name': full_name,
                    'last_name': last_name[:50],
                    'first_name': first_name[:50],
                    'patronymic_name': patronymic_name[:50],
                    'sam_account_name': (row[2] or '').strip()[:100],
                    'email': (row[3] or '').strip(),
                    'department': (row[5] or '').strip()[:150],
                    'job_title': (row[6] or '').strip()[:150],
                    'company': company,
                    'active': True,
                }

                emp, created = Employee.objects.update_or_create(
                    guid=guid,
                    defaults=defaults
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            # Деактивация удалённых
            deactivated = Employee.objects.filter(active=True).exclude(guid__in=active_guids).update(active=False)

            # Обновляем время последней синхронизации
            settings.last_sync = now
            settings.save()

            self.stdout.write(self.style.SUCCESS(
                f'Синхронизация завершена:\n'
                f'  + создано: {created_count}\n'
                f'  обновлено: {updated_count}\n'
                f'  деактивировано: {deactivated}'
            ))

        except pyodbc.Error as e:
            self.stdout.write(self.style.ERROR(f'Ошибка подключения к MSSQL: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Общая ошибка: {e}'))
        finally:
            if 'conn' in locals():
                conn.close()