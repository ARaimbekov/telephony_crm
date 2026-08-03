from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from leads.models import Apparats, Atc, Company, EmployeeDwh, Lead, Number
from leads.views import _name_search_query


class LeadNameSearchTest(TestCase):
    def setUp(self):
        self.atc = Atc.objects.create(name="ATC", ip_address="127.0.0.1")
        self.company = Company.objects.create(name="Company")
        self.phone_model = Apparats.objects.create(name="Phone")
        self.employee = EmployeeDwh.objects.create(
            guid_nsi=uuid4(),
            full_name="Калычев Николай Сергеевич",
            samaccountname="Kalychev_NS",
            company="Company",
            department="IT",
            job_title="Engineer",
        )
        self.lead = Lead.objects.create(
            phone_number=Number.objects.create(name="1001", atc=self.atc),
            mac_address="000000000001",
            last_name="Калычев",
            first_name="Н",
            patronymic_name="С",
        )
        self.lead.atc.add(self.atc)
        self.lead.company.add(self.company)
        self.lead.phone_model.add(self.phone_model)
        self.lead.employees.add(self.employee)

    def search(self, query):
        return Lead.objects.filter(_name_search_query(query)).distinct()

    def test_searches_generated_employee_display_name(self):
        self.assertQuerysetEqual(self.search("Калычев Н.С."), [self.lead])

    def test_searches_employee_full_name(self):
        self.assertQuerysetEqual(self.search("Николай Сергеевич"), [self.lead])

    def test_searches_manual_display_name(self):
        self.lead.display_name = "Дежурный столовой"
        self.lead.save(update_fields=["display_name"])

        self.assertQuerysetEqual(self.search("столовой"), [self.lead])


class LeadCreateErrorHandlingTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user", password="pass")
        self.atc = Atc.objects.create(name="ATC", ip_address="127.0.0.1")
        self.company = Company.objects.create(name="Company")
        self.phone_model = Apparats.objects.create(name="Phone")
        self.number = Number.objects.create(name="1002", atc=self.atc)
        self.employee = EmployeeDwh.objects.create(
            guid_nsi=uuid4(),
            full_name="Зайцев Евгений Вадимович",
            samaccountname="Zaytsev_EV",
            company="Company",
            department="IT",
            job_title="Engineer",
        )

    def make_lead(self):
        lead = Lead.objects.create(
            phone_number=self.number,
            mac_address="000000000002",
            last_name="Зайцев",
            first_name="Е",
            patronymic_name="В",
        )
        lead.atc.add(self.atc)
        lead.company.add(self.company)
        lead.phone_model.add(self.phone_model)
        lead.employees.add(self.employee)
        return lead

    def update_payload(self, lead, mac_address):
        return {
            "atc": [str(self.atc.id)],
            "phone_number": str(lead.phone_number_id),
            "mac_address": mac_address,
            "line": lead.line,
            "phone_model": [str(self.phone_model.id)],
            "employees": [str(self.employee.id)],
            "external_line_access": lead.external_line_access,
            "timezone": lead.timezone,
        }

    def test_missing_employees_shows_form_error_not_mac_error(self):
        self.client.login(username="user", password="pass")

        response = self.client.post(reverse("leads:lead-create"), {
            "atc": [str(self.atc.id)],
            "phone_number": str(self.number.id),
            "mac_address": "00-00-00-00-00-02",
            "line": "1",
            "phone_model": [str(self.phone_model.id)],
            "external_line_access": "локальные_МГ",
            "timezone": "+8",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "leads/lead_create.html")
        self.assertContains(response, "Выберите сотрудника")
        self.assertEqual(Lead.objects.count(), 0)

    def test_invalid_mac_format_shows_mac_error_not_form_error(self):
        self.client.login(username="user", password="pass")

        response = self.client.post(reverse("leads:lead-create"), {
            "atc": [str(self.atc.id)],
            "phone_number": str(self.number.id),
            "mac_address": "00-00-00",
            "line": "1",
            "phone_model": [str(self.phone_model.id)],
            "external_line_access": "локальные_МГ",
            "timezone": "+8",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "error_mac_failed.html")
        self.assertEqual(Lead.objects.count(), 0)

    def test_invalid_mac_chars_shows_mac_type_error(self):
        self.client.login(username="user", password="pass")

        response = self.client.post(reverse("leads:lead-create"), {
            "atc": [str(self.atc.id)],
            "phone_number": str(self.number.id),
            "mac_address": "not-a-mac",
            "line": "1",
            "phone_model": [str(self.phone_model.id)],
            "external_line_access": "локальные_МГ",
            "timezone": "+8",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "error_mac_type_failed.html")
        self.assertEqual(Lead.objects.count(), 0)

    def test_update_invalid_mac_format_shows_mac_error_and_does_not_save(self):
        self.client.login(username="user", password="pass")
        lead = self.make_lead()

        response = self.client.post(
            reverse("leads:lead-update", kwargs={"pk": lead.pk}),
            self.update_payload(lead, "00-00-00"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "error_mac_failed.html")
        lead.refresh_from_db()
        self.assertEqual(lead.mac_address, "000000000002")

    def test_update_invalid_mac_chars_shows_mac_type_error_and_does_not_save(self):
        self.client.login(username="user", password="pass")
        lead = self.make_lead()

        response = self.client.post(
            reverse("leads:lead-update", kwargs={"pk": lead.pk}),
            self.update_payload(lead, "not-a-mac"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "error_mac_type_failed.html")
        lead.refresh_from_db()
        self.assertEqual(lead.mac_address, "000000000002")

    def test_update_valid_mac_normalizes_and_saves(self):
        self.client.login(username="user", password="pass")
        lead = self.make_lead()

        response = self.client.post(
            reverse("leads:lead-update", kwargs={"pk": lead.pk}),
            self.update_payload(lead, "00:00:00:00:00:03"),
        )

        self.assertEqual(response.status_code, 302)
        lead.refresh_from_db()
        self.assertEqual(lead.mac_address, "000000000003")


class LeadUpdateMacValidationTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user", password="pass")
        self.atc = Atc.objects.create(name="ATC", ip_address="127.0.0.1")
        self.company = Company.objects.create(name="Company")
        self.phone_model = Apparats.objects.create(name="Phone")
        self.number = Number.objects.create(name="1003", atc=self.atc)
        self.lead = Lead.objects.create(
            phone_number=self.number,
            mac_address="000000000003",
            last_name="Калычев",
            first_name="Н",
            patronymic_name="С",
        )
        self.lead.atc.add(self.atc)
        self.lead.company.add(self.company)
        self.lead.phone_model.add(self.phone_model)

    def post_update(self, mac_address):
        self.client.login(username="user", password="pass")
        return self.client.post(reverse("leads:lead-update", args=[self.lead.pk]), {
            "atc": [str(self.atc.id)],
            "phone_number": str(self.number.id),
            "mac_address": mac_address,
            "line": "1",
            "phone_model": [str(self.phone_model.id)],
            "external_line_access": "локальные_МГ",
            "timezone": "+8",
        })

    def test_invalid_mac_chars_on_update_shows_mac_type_error_and_does_not_save(self):
        response = self.post_update("not-a-mac")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "error_mac_type_failed.html")

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.mac_address, "000000000003")

    def test_invalid_mac_format_on_update_shows_mac_error_and_does_not_save(self):
        response = self.post_update("00-00-00")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "error_mac_failed.html")

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.mac_address, "000000000003")

    def test_valid_mac_on_update_is_normalized(self):
        response = self.post_update("00:00:00:00:00:04")

        self.assertEqual(response.status_code, 302)

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.mac_address, "000000000004")
