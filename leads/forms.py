from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UsernameField
from .models import Lead, Company, Apparats, Number, Atc
from itertools import chain
from django.db.models import Count
from django.forms import inlineformset_factory


User = get_user_model()

class LeadCreateModelForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = (
            'reservation',
            'mac_address',
            'last_name',
            'first_name',
            'patronymic_name',
            'phone_model',
            'company',
            'line',
            'active',
        )

    def __init__(self,*args,**kwargs):
        super(LeadCreateModelForm, self).__init__(*args,**kwargs)
        # numbers = Lead.objects.all().values('phone_number')
        # self.fields['phone_number'].queryset = Number.objects.exclude(id__in=numbers)
        # self.fields['phone_number'].empty_label = "номер телефона не выбран"
        self.fields['company'].empty_label = "компания не выбрана"
        self.fields['phone_model'].empty_label = "модель телефона не выбрана"
        # self.fields['atc'].queryset = Atc.objects.filter(name__in=atc)

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]

        return data



    def clean(self):
        # cleaned_data = self.cleaned_data
        # if Lead.objects.filter(mac_address=cleaned_data['mac_address'], line=self.line).exists():

        #     raise ValidationError(
        #           'Solution with this Name already exists for this problem')

        # return cleaned_data
        pass


# class LeadUpdateModelForm(forms.ModelForm):
#     class Meta:
#         model = Lead
#         fields = (
#             'phone_number',
#             'mac_address',
#             'first_name',
#             'last_name',
#             'patronymic_name',
#             'phone_model',
#             'company',
#             'active',
#         )


#     def __init__(self, *args, **kwargs):
#         super(LeadUpdateModelForm, self).__init__(*args,**kwargs)
#         numbers = Lead.objects.all().values('phone_number')
        
#         self.fields['phone_number'].queryset = Number.objects.exclude(id__in=numbers)

#     def clean_first_name(self):
#         data = self.cleaned_data["first_name"]
#         return data

#     def clean(self):
#         pass


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


class CompanyModelForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            'name',
        )


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        # if data != "Joe":
        #     raise ValidationError("Your name is not Joe")
        return data

    def clean(self):
        pass
        # first_name = self.cleaned_data["first_name"]
        # last_name = self.cleaned_data["last_name"]
        # if first_name + last_name != "Joe Soap":
        #     raise ValidationError("Your name is not Joe Soap")


class ApparatModelForm(forms.ModelForm):
    class Meta:
        model = Apparats
        fields = (
            'name',
        )


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        # if data != "Joe":
        #     raise ValidationError("Your name is not Joe")
        return data

    def clean(self):
        pass
        # first_name = self.cleaned_data["first_name"]
        # last_name = self.cleaned_data["last_name"]
        # if first_name + last_name != "Joe Soap":
        #     raise ValidationError("Your name is not Joe Soap")


class NumberModelForm(forms.ModelForm):
    class Meta:
        model = Number
        fields = (
            'name',
            'atc',
        )


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        # if data != "Joe":
        #     raise ValidationError("Your name is not Joe")
        return data

    def clean(self):
        pass
        # first_name = self.cleaned_data["first_name"]
        # last_name = self.cleaned_data["last_name"]
        # if first_name + last_name != "Joe Soap":
        #     raise ValidationError("Your name is not Joe Soap")


class AtcModelForm(forms.ModelForm):
    class Meta:
        model = Atc
        fields = (
            'name',
            'ip_address',
        )


    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        # if data != "Joe":
        #     raise ValidationError("Your name is not Joe")
        return data

    def clean(self):
        pass
        # first_name = self.cleaned_data["first_name"]
        # last_name = self.cleaned_data["last_name"]
        # if first_name + last_name != "Joe Soap":
        #     raise ValidationError("Your name is not Joe Soap")


class LeadForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    age = forms.IntegerField(min_value=0)


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username",)
        field_classes = {'username': UsernameField}


# class AssignAgentForm(forms.Form):
#     # agent = forms.ModelChoiceField(queryset=Agent.objects.none())

#     def __init__(self, *args, **kwargs):
#         request = kwargs.pop("request")
#         agents = Agent.objects.filter(organisation=request.user.userprofile)
#         super(AssignAgentForm, self).__init__(*args, **kwargs)
#         self.fields["agent"].queryset = agents


# class LeadCategoryUpdateForm(forms.ModelForm):
#     class Meta:
#         model = Lead
#         fields = (
#             'category',
#         )


# class CategoryModelForm(forms.ModelForm):
#     class Meta:
#         model = Category
#         fields = (
#             'name',
#         )


# class FollowUpModelForm(forms.ModelForm):
#     class Meta:
#         model = FollowUp
#         fields = (
#             'notes',
#             'file'
#         )