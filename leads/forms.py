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

User = get_user_model()

class LeadCreateModelForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = (
            'atc',
            'phone_number',
            'reservation',
            'mac_address',
            'line',
            'last_name',
            'first_name',
            'patronymic_name',
            'phone_model',
            'company',
            'active',
        )

    def __init__(self,*args,**kwargs):
        super(LeadCreateModelForm, self).__init__(*args,**kwargs)
        self.fields['atc'].empty_label = "ATC не выбрана"
        self.fields['phone_number'].empty_label = "номер телефона не выбран"
        self.fields['company'].empty_label = "компания не выбрана"
        self.fields['phone_model'].empty_label = "модель телефона не выбрана"
        

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data



    def clean(self):
        pass


class LeadModelForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = (
            'phone_number',
            'mac_address',
            'first_name',
            'last_name',
            'patronymic_name',
            'phone_model',
            'company',
            'line',
            'atc',
            'active',
            'reservation',
        )
        

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
            'password',
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
        fields = (
            'username',
        )
        

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
        