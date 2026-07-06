from dataclasses import Field
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UsernameField
from .models import Lead, Company, Apparats, Number, Atc
from itertools import chain
from django.db.models import Count
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Fieldset,Field
from .models import Lead, Company, Apparats, Number, Atc, EmployeeDwh
from django.db import transaction



User = get_user_model()

from django.db import transaction
from django.db.models import Q


def format_employee_label(employee):
    company = (employee.company or "").strip() or "Без компании"
    samaccountname = (employee.samaccountname or "").strip()
    job_title = (employee.job_title or "").strip() or "Без должности"
    full_name = (employee.full_name or "").strip()
    name_with_account = f"{full_name} ({samaccountname})" if samaccountname else full_name
    return f"{name_with_account} — {company} — {job_title}"


def _parse_full_name(full_name: str):
    parts = (full_name or "").strip().split()
    last = parts[0] if len(parts) > 0 else ""
    first = parts[1] if len(parts) > 1 else ""
    patronymic = parts[2] if len(parts) > 2 else ""
    return last, first, patronymic


class EmployeeChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return format_employee_label(obj)


class LeadCreateModelForm(forms.ModelForm):
    employees = EmployeeChoiceField(
        label="Сотрудники",
        required=True,
        queryset=EmployeeDwh.objects.none(),
        widget=forms.SelectMultiple(attrs={
            "id": "id_employees",
            "class": "select2-employee",
            "multiple": "multiple",
        })
    )


    class Meta:
        model = Lead
        fields = "__all__"
        # скрываем ручной ввод ФИО и компанию в форме создания
        exclude = ("first_name", "last_name", "patronymic_name", "company")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["display_name"].widget.attrs["autocomplete"] = "off"

        self.fields['atc'].empty_label = "ATC не выбрана"
        self.fields['phone_number'].empty_label = "номер телефона не выбран"
        self.fields['phone_model'].empty_label = "модель телефона не выбрана"

        selected_ids = []
        if self.data:
            selected_ids = [x for x in self.data.getlist("employees") if str(x).isdigit()]
        elif self.instance and self.instance.pk:
            selected_ids = list(self.instance.employees.values_list("id", flat=True))

        if selected_ids:
            self.fields["employees"].queryset = EmployeeDwh.objects.filter(
                status=EmployeeDwh.Status.ACTIVE,
                id__in=selected_ids
            )
        else:
            self.fields["employees"].queryset = EmployeeDwh.objects.none()



    def clean(self):
        cleaned = super().clean()
        employees = cleaned.get("employees")
        if not employees:
            raise ValidationError("Выберите сотрудника из справочника (EmployeeDwh).")
        return cleaned


    @transaction.atomic
    def save(self, commit=True):
        lead = super().save(commit=False)

        employees = self.cleaned_data["employees"]
        primary = employees.first()

        if primary:
            last, first, patronymic = _parse_full_name(primary.full_name)
            lead.last_name = last or ""
            lead.first_name = first or ""
            lead.patronymic_name = patronymic or ""

        if commit:
            lead.save()
            lead.employees.set(employees)

            if primary and (primary.company or "").strip():
                comp_obj, _ = Company.objects.get_or_create(name=primary.company.strip())
                lead.company.set([comp_obj])
            else:
                lead.company.clear()

            self.save_m2m()

        return lead

class LeadModelForm(forms.ModelForm):
    employees = EmployeeChoiceField(
        label="Сотрудники",
        required=False,
        queryset=EmployeeDwh.objects.none(),
        widget=forms.SelectMultiple(attrs={
            "id": "id_employees",
            "class": "select2-employee",
            "multiple": "multiple",
        })
    )

    class Meta:
        model = Lead
        fields = "__all__"
        exclude = ("first_name", "last_name", "patronymic_name", "company")

        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        selected_ids = []
        if self.data:
            selected_ids = [x for x in self.data.getlist("employees") if str(x).isdigit()]            
        elif self.instance and self.instance.pk:
            selected_ids = list(self.instance.employees.values_list("id", flat=True))

        # чтобы на странице редактирования показывались уже выбранные
        if (not self.data) and self.instance and self.instance.pk:
            self.initial["employees"] = selected_ids

        if selected_ids:
            self.fields["employees"].queryset = EmployeeDwh.objects.filter(id__in=selected_ids)
        else:
            self.fields["employees"].queryset = EmployeeDwh.objects.none()


    @transaction.atomic
    def save(self, commit=True):
        lead = super().save(commit=False)

        employees = self.cleaned_data.get("employees")
        if employees is not None:
            primary = employees.first()

            if primary:
                last, first, patronymic = _parse_full_name(primary.full_name)
                lead.last_name = last or ""
                lead.first_name = first or ""
                lead.patronymic_name = patronymic or ""

            if commit:
                lead.save()
                lead.employees.set(employees)

                if primary and (primary.company or "").strip():
                    comp_obj, _ = Company.objects.get_or_create(name=primary.company.strip())
                    lead.company.set([comp_obj])
                else:
                    lead.company.clear()

                self.save_m2m()
                return lead

        # если employees не прислали (редкий кейс)
        if commit:
            lead.save()
            self.save_m2m()
        return lead

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data

    def clean(self):
        pass


class LeadDelModelForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ()
        

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data

    def clean(self):
        
        pass


class CompanyDelModelForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ()
        

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data

    def clean(self):
        pass


class ApparatDelModelForm(forms.ModelForm):
    class Meta:
        model = Apparats
        fields = ()
        

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data

    def clean(self):
        pass


class NumberDelModelForm(forms.ModelForm):
    class Meta:
        model = Apparats
        fields = ()
        

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data

    def clean(self):
        pass        


class UserModelForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'username',
            'is_superuser',
            'is_active',
            'first_name',
            'last_name',
        )
        

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data

    def clean(self):
        pass


class UserDelModelForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ()
        

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data

    def clean(self):
        pass



class SetPasswordForm(SetPasswordForm):
    class Meta:
        model = get_user_model()
        fields = ['new_password1', 'new_password2']


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data

    def clean(self):
        pass

        

class CompanyModelForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            'name',
        )


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        return data


    def clean(self):
        
        pass



class ApparatModelForm(forms.ModelForm):
    class Meta:
        model = Apparats
        fields = (
            'name',
        )


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        return data


    def clean(self):
        pass



class NumberModelForm(forms.ModelForm):
    class Meta:
        model = Number
        fields = (
            'name',
            'atc',
        )


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        return data


    def clean(self):
        pass



class AtcModelForm(forms.ModelForm):
    class Meta:
        model = Atc
        fields = (
            'name',
            'ip_address',
        )


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        return data


    def clean(self):
        pass



class LeadForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    age = forms.IntegerField(min_value=0)


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "username",
            "is_superuser",
            "first_name",
            "last_name",
        )
        field_classes = {'username': UsernameField}
        
