from dataclasses import Field
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UsernameField
from .models import Lead, Company, Apparats, Number, Atc, Employee
from itertools import chain
from django.db.models import Count
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Fieldset,Field

User = get_user_model()

class LeadCreateModelForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = "__all__"
        widgets = {
            'employees': forms.SelectMultiple(attrs={
                'class': 'form-control select2-ajax',
                'multiple': 'multiple',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ... твои настройки empty_label ...

        # employees — теперь AJAX, queryset не нужен
        self.fields['employees'].required = False
        # Убираем старые ФИО из формы (скрываем)
        self.fields['first_name'].widget = forms.HiddenInput()
        self.fields['last_name'].widget = forms.HiddenInput()
        self.fields['patronymic_name'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        employees = cleaned_data.get('employees', [])
        companies = cleaned_data.get('company', [])

        if employees:
            if not companies.exists():
                raise ValidationError("Выберите хотя бы одну компанию, чтобы привязать сотрудника.")

            lead_companies = set(companies.values_list('name', flat=True))

            mismatches = []
            for emp in employees:
                emp_company = (emp.company_text or '').strip()
                if emp_company and emp_company not in lead_companies:
                    mismatches.append(f"{emp.full_name} ({emp_company})")

            if mismatches:
                raise ValidationError(
                    "Компания сотрудника не совпадает с выбранными компаниями лида:\n" +
                    "\n".join(mismatches)
                )

        return cleaned_data

        
    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data


class LeadModelForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = "__all__"
        widgets = {
            "employees": forms.SelectMultiple(attrs={"multiple": "multiple"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employees"].required = False
        self.fields["employees"].queryset = Employee.objects.none()

        

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
        