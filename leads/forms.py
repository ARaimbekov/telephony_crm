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
        exclude = ['company', 'first_name', 'last_name', 'patronymic_name']  # Убрали company и ФИО

    widgets = {
        'employees': forms.SelectMultiple(attrs={
            'class': 'form-control select2-ajax',
            'multiple': 'multiple',
            'data-placeholder': 'Начните вводить ФИО / компанию / должность...',
        }),
        'display_name': forms.TextInput(attrs={'placeholder': 'Автогенерация или вручную'}),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Плейсхолдеры для других полей
        self.fields['atc'].empty_label = "ATC не выбрана"
        self.fields['phone_number'].empty_label = "Номер телефона не выбран"
        self.fields['phone_model'].empty_label = "Модель телефона не выбрана"

        self.fields['employees'].required = False

        # Скрываем ФИО и company
        for field in ['first_name', 'last_name', 'patronymic_name', 'company']:
            self.fields[field].widget = forms.HiddenInput()
            self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        employees = cleaned_data.get('employees', [])

        if not employees:
            return cleaned_data

        # Собираем уникальные названия компаний из company_text
        company_names = {emp.company_text.strip() for emp in employees if emp.company_text}

        if not company_names:
            raise ValidationError("У выбранных сотрудников нет компании — обратитесь в тех. поддержку.")

        # Проверяем наличие в базе
        mismatches = []
        valid_companies = []
        for name in company_names:
            try:
                comp = Company.objects.get(name__iexact=name)
                valid_companies.append(comp)
            except Company.DoesNotExist:
                mismatches.append(name)

        if mismatches:
            raise ValidationError(
                f"Нет такой компании в системе: {', '.join(mismatches)}. "
                f"Обратитесь в тех. поддержку."
            )

        # Записываем компании в cleaned_data
        cleaned_data['company'] = valid_companies

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Автогенерация display_name
        if not instance.display_name and instance.employees.exists():
            names = [emp.full_name.split()[0] for emp in instance.employees.all()[:3]]
            phone = instance.phone_number.name if instance.phone_number else 'номер'
            instance.display_name = " / ".join(names) + f" — {phone}"

        if commit:
            instance.save()
            self.save_m2m()  # сохраняет employees и company

        return instance
        

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
        