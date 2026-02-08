import pyodbc
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import IntegrityError
from leads.models import Employee, Company, SyncSettings

class Command(BaseCommand):
    help = 'Синхронизация сотрудников из MSSQL в модель Employee'

    def handle(self, *args, **options):
        settings = SyncSettings.get_settings()
        now = timezone.now()

        # Проверка интервала
        if settings.last_sync:
            hours_passed = (now - settings.last_sync).total_seconds() / 3600
            if hours_passed < settings.interval_hours:
                self.stdout.write(self.style.WARNING(
                    f'Ещё рано для синхронизации: прошло {hours_passed:.1f} часов из {settings.interval_hours}'
                ))
                return

        # Проверка ночного времени
#        if settings.night_only and not (0 <= now.hour < 6):
#            self.stdout.write(self.style.WARNING('Синхронизация только ночью (00:00–06:00)'))
#            return

        # Строка подключения к MSSQL
        conn_str = (
            'DRIVER={ODBC Driver 18 for SQL Server};'
            'SERVER=ink-sqlsrv-dwh;'
            'DATABASE=DWH;'
            'UID=info_conferences;'
            'PWD={lzxV9TF);*jpucr9BkXb};'
            'Encrypt=no;'
            'TrustServerCertificate=yes;'
        )

        conn = None
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
            skipped_count = 0

            for row in rows:
                guid = str(row[0]).strip()
                active_guids.add(guid)

                # === ИСПРАВЛЕНО: обрезаем full_name до 100 символов ===
                full_name = (row[1].strip() if row[1] else '')[:100]
                name_parts = full_name.split()
                last_name = name_parts[0] if name_parts else ''
                first_name = name_parts[1] if len(name_parts) > 1 else ''
                patronymic_name = ' '.join(name_parts[2:]) if len(name_parts) > 2 else ''

                # === ИСПРАВЛЕНО: обрезаем название компании до 255 символов ===
                company_name = (row[4].strip() if row[4] else 'Не указано')[:255]
                company, _ = Company.objects.get_or_create(name=company_name)

                defaults = {
                    'full_name': full_name,  # ← Теперь безопасно (≤100)
                    'last_name': last_name[:50],
                    'first_name': first_name[:50],
                    'patronymic_name': patronymic_name[:50],
                    'sam_account_name': (row[2] or '').strip()[:100],
                    'email': (row[3] or '').strip()[:254],  # ← Безопасно (≤254)
                    'department': (row[5] or '').strip()[:150],
                    'job_title': (row[6] or '').strip()[:150],
                    'company': company,
                    'active': True,
                }

                try:
                    emp, created = Employee.objects.update_or_create(
                        guid=guid,
                        defaults=defaults
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f'Создан: {guid} ({full_name})')
                    else:
                        updated_count += 1
                        self.stdout.write(f'Обновлён: {guid} ({full_name})')

                except IntegrityError as ie:
                    # Дубликат уникального поля (скорее всего sam_account_name)
                    self.stdout.write(self.style.WARNING(
                        f'Дубликат sam_account_name "{defaults["sam_account_name"]}" (guid: {guid}) — обновляем существующую запись'
                    ))
                    try:
                        emp = Employee.objects.get(guid=guid)
                        for key, value in defaults.items():
                            setattr(emp, key, value)
                        emp.save()
                        updated_count += 1
                    except Employee.DoesNotExist:
                        self.stdout.write(self.style.ERROR(
                            f'Ошибка: запись с guid {guid} не найдена для обновления'
                        ))
                    except Exception as inner_e:
                        self.stdout.write(self.style.ERROR(
                            f'Ошибка обновления дубликата {guid}: {inner_e}'
                        ))
                    skipped_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'Ошибка записи сотрудника {guid} ({full_name}): {e}'
                    ))
                    skipped_count += 1

            # Деактивация удалённых из MSSQL
            deactivated = Employee.objects.filter(active=True).exclude(guid__in=active_guids).update(active=False)
            if deactivated:
                self.stdout.write(f'Деактивировано записей: {deactivated}')

            # Обновляем время последней синхронизации
            settings.last_sync = now
            settings.save()

            self.stdout.write(self.style.SUCCESS(
                f'\nСинхронизация завершена:\n'
                f'  + создано: {created_count}\n'
                f'  обновлено: {updated_count}\n'
                f'  пропущено/ошибок: {skipped_count}\n'
                f'  деактивировано: {deactivated}'
            ))

        except pyodbc.Error as e:
            self.stdout.write(self.style.ERROR(f'Ошибка подключения к MSSQL: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Общая ошибка: {e}'))
        finally:
            if conn:
                conn.close()
