import csv
import io
import tempfile
from pathlib import Path
from uuid import uuid4

from django.core.management import call_command
from django.test import TestCase

from leads.models import Atc, Company, EmployeeDwh, Lead, Number


class LinkLeadsToDwhCommandTest(TestCase):
    def setUp(self):
        self.atc = Atc.objects.create(name="ATC", ip_address="127.0.0.1")
        self.old_company = Company.objects.create(name="Old Company")

    def make_lead(self, number, last_name, first_name, patronymic_name):
        phone_number = Number.objects.create(name=number, atc=self.atc)
        lead = Lead.objects.create(
            phone_number=phone_number,
            mac_address=f"0000000000{number[-2:]}",
            last_name=last_name,
            first_name=first_name,
            patronymic_name=patronymic_name,
        )
        lead.company.add(self.old_company)
        return lead

    def make_employee(self, full_name, company="New Company"):
        return EmployeeDwh.objects.create(
            guid_nsi=uuid4(),
            full_name=full_name,
            samaccountname=full_name.split()[0].lower(),
            mail="user@example.com",
            company=company,
            department="IT",
            job_title="Engineer",
        )

    def run_command(self):
        report_path = Path(tempfile.gettempdir()) / f"link_leads_to_dwh_{uuid4()}.csv"
        call_command("link_leads_to_dwh", report_path=str(report_path), stdout=io.StringIO())
        with report_path.open(encoding="utf-8-sig", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file, delimiter=";"))
        return rows

    def test_links_unique_match_by_initials_and_keeps_existing_company(self):
        lead = self.make_lead("1001", "Зайцев", "Е", "В")
        employee = self.make_employee("Зайцев Евгений Вадимович", company="АО Новая Компания")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertQuerysetEqual(lead.employees.all(), [employee])
        self.assertEqual(list(lead.company.values_list("name", flat=True)), ["Old Company"])
        self.assertEqual(rows[0]["status"], "linked")
        self.assertEqual(rows[0]["match_rule"], "initials")
        self.assertEqual(rows[0]["lead_initials_key"], "зайцев е в")
        self.assertIn("инициал е совпал", rows[0]["fio_differences"])

    def test_links_dotted_initials(self):
        lead = self.make_lead("1004", "Журавлев", "А.К.", "")
        employee = self.make_employee("Журавлев Алеся Канева")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertQuerysetEqual(lead.employees.all(), [employee])
        self.assertEqual(rows[0]["status"], "linked")
        self.assertEqual(rows[0]["match_rule"], "initials")
        self.assertEqual(rows[0]["lead_initials_key"], "журавлев а к")

    def test_links_compact_initials(self):
        lead = self.make_lead("1005", "Сергаков", "ВА", "")
        employee = self.make_employee("Сергаков Виктор Аркадьевич")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertQuerysetEqual(lead.employees.all(), [employee])
        self.assertEqual(rows[0]["status"], "linked")
        self.assertEqual(rows[0]["match_rule"], "initials")
        self.assertEqual(rows[0]["lead_initials_key"], "сергаков в а")

    def test_links_initials_after_company_prefix_in_last_name(self):
        lead = self.make_lead("1007", "ИЗП Маркова ОА", "", "")
        employee = self.make_employee("Маркова Ольга Александровна")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertQuerysetEqual(lead.employees.all(), [employee])
        self.assertEqual(rows[0]["status"], "linked")
        self.assertEqual(rows[0]["match_rule"], "initials")
        self.assertEqual(rows[0]["lead_fio"], "ИЗП Маркова ОА")
        self.assertEqual(rows[0]["lead_initials_key"], "маркова о а")

    def test_links_dotted_initials_after_company_prefix(self):
        lead = self.make_lead("1008", "ИЗП Маркова О. А.", "", "")
        employee = self.make_employee("Маркова Ольга Александровна")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertQuerysetEqual(lead.employees.all(), [employee])
        self.assertEqual(rows[0]["status"], "linked")
        self.assertEqual(rows[0]["match_rule"], "initials")
        self.assertEqual(rows[0]["lead_initials_key"], "маркова о а")

    def test_links_initials_after_multiple_prefix_words(self):
        lead = self.make_lead("1009", "УК ГПЗ Лукманова", "Ю.В", "")
        employee = self.make_employee("Лукманова Юлия Викторовна")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertQuerysetEqual(lead.employees.all(), [employee])
        self.assertEqual(rows[0]["status"], "linked")
        self.assertEqual(rows[0]["match_rule"], "initials")
        self.assertEqual(rows[0]["lead_initials_key"], "лукманова ю в")

    def test_links_initials_after_inks_prefix(self):
        lead = self.make_lead("1010", "ИНКС Непомнящая", "НЛ", "")
        employee = self.make_employee("Непомнящая Наталья Леонидовна")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertQuerysetEqual(lead.employees.all(), [employee])
        self.assertEqual(rows[0]["status"], "linked")
        self.assertEqual(rows[0]["match_rule"], "initials")
        self.assertEqual(rows[0]["lead_initials_key"], "непомнящая н л")

    def test_does_not_strip_prefix_when_lead_contains_slash(self):
        lead = self.make_lead("1011", "ИЗП Глумова/Харасов", "", "")
        self.make_employee("Глумова Ольга Александровна")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertEqual(lead.employees.count(), 0)
        self.assertEqual(rows[0]["status"], "not_found")
        self.assertEqual(rows[0]["match_rule"], "no_initials_key")

    def test_does_not_link_initials_when_lead_contains_multiple_people(self):
        lead = self.make_lead("1006", "Клачков", "М.Ю.", "Скрастин В.Б.")
        self.make_employee("Клачков Михаил Юрьевич")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertEqual(lead.employees.count(), 0)
        self.assertEqual(rows[0]["status"], "not_found")
        self.assertEqual(rows[0]["match_rule"], "no_initials_key")

    def test_does_not_link_ambiguous_initials(self):
        lead = self.make_lead("1002", "Зайцев", "Е", "В")
        self.make_employee("Зайцев Евгений Вадимович")
        self.make_employee("Зайцев Егор Васильевич")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertEqual(lead.employees.count(), 0)
        self.assertEqual(rows[0]["status"], "ambiguous")
        self.assertEqual(rows[0]["candidates_count"], "2")
        self.assertIn("Найдено несколько кандидатов", rows[0]["match_reason"])

    def test_reports_not_found_without_changing_lead(self):
        lead = self.make_lead("1003", "Масалов", "О", "А")
        self.make_employee("Масалов Сергей Иванович")

        rows = self.run_command()

        lead.refresh_from_db()
        self.assertEqual(lead.employees.count(), 0)
        self.assertEqual(list(lead.company.values_list("name", flat=True)), ["Old Company"])
        self.assertEqual(rows[0]["status"], "not_found")
        self.assertEqual(rows[0]["same_last_name_count"], "1")
        self.assertIn("Масалов Сергей Иванович", rows[0]["same_last_name_candidates"])
        self.assertIn("имя: Lead о != DWH сергей", rows[0]["fio_differences"])
