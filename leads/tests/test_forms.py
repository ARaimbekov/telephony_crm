from uuid import uuid4

from django.test import TestCase

from leads.forms import LeadModelForm
from leads.models import Apparats, Atc, Company, EmployeeDwh, Lead, Number


class LeadDisplayNameTest(TestCase):
    def setUp(self):
        self.atc = Atc.objects.create(name="ATC", ip_address="127.0.0.1")
        self.company = Company.objects.create(name="Old Company")
        self.phone_model = Apparats.objects.create(name="Phone")
        self.number = Number.objects.create(name="1001", atc=self.atc)
        self.employee = EmployeeDwh.objects.create(
            guid_nsi=uuid4(),
            full_name="Калычев Николай Сергеевич",
            samaccountname="Kalychev_NS",
            company="ООО ИНК-Синергия",
            department="IT",
            job_title="Engineer",
        )

    def make_lead(self, display_name=""):
        lead = Lead.objects.create(
            phone_number=self.number,
            mac_address="000000000001",
            last_name="Калычев",
            first_name="Н",
            patronymic_name="С",
            display_name=display_name,
        )
        lead.atc.add(self.atc)
        lead.phone_model.add(self.phone_model)
        lead.company.add(self.company)
        lead.employees.add(self.employee)
        return lead

    def test_actual_display_name_uses_generated_name_without_saving_it(self):
        lead = self.make_lead()

        self.assertEqual(lead.generated_display_name, "Калычев Н.С.")
        self.assertEqual(lead.actual_display_name, "Калычев Н.С.")

        lead.refresh_from_db()
        self.assertEqual(lead.display_name, "")

    def test_manual_display_name_has_priority(self):
        lead = self.make_lead(display_name="Дежурный столовой")

        self.assertEqual(lead.generated_display_name, "Калычев Н.С.")
        self.assertEqual(lead.actual_display_name, "Дежурный столовой")

    def test_form_uses_generated_display_name_as_placeholder(self):
        lead = self.make_lead()

        form = LeadModelForm(instance=lead)

        self.assertEqual(form.fields["display_name"].widget.attrs["placeholder"], "Калычев Н.С.")
