import csv
import xlwt
import logging
import datetime
from django import contrib
from django.contrib import messages
from django.core.mail import send_mail
from django.http.response import JsonResponse
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import generic
from agents.mixins import OrganisorAndLoginRequiredMixin
from .models import Lead, Company, Apparats, Number
from .forms import (
    LeadForm, 
    LeadCreateModelForm, 
    LeadModelForm,
    CompanyModelForm,
    ApparatModelForm,
    NumberModelForm,
    CustomUserCreationForm,
)


logger = logging.getLogger(__name__)


def export_to_csv(reuest): 
    row_num = 0 
    leads = Lead.objects.all() 
    response = HttpResponse('') 
    response['Content-Disposition'] = 'attachment; filename=profile_export.csv'
    writer = csv.writer(response,  delimiter =';',quotechar =',') 
    writer.writerow([
        'first_name', 
        'last_name', 
        'patronymic_name', 
        'phone_number', 
        'mac_address', 
        'phone_model', 
        'company',
        'line',
        'atc',
        'date_added', 
        'update_added', 
        'active'
        ])

    rows = leads.values_list(
        'first_name', 
        'last_name', 
        'patronymic_name', 
        'phone_number', 
        'mac_address', 
        'phone_model', 
        'company', 
        'line',
        'atc',
        'date_added', 
        'update_added', 
        'active'
    )

    for row in rows:
        row_list = list (row)
        row_list[3] = Number.objects.get(pk=row_list[3])
        row_list[5] = Apparats.objects.get(pk=row_list[5])
        row_list[6] = Company.objects.get(pk=row_list[6])
        row=tuple(row_list)
        writer.writerow(row) 

    return response 



def export_to_exel(request):
    response = HttpResponse(content_type='application/ms-excel') 
    response['Content-Disposition'] = 'attachment; filename=Expenses' + str(datetime.datetime.now())+'.xls' 
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Выгрузка-таблицы ') 
    row_num = 0 
    font_style = xlwt.XFStyle()
    font_style.font.bold = True 

    columns = (
        'first_name', 
        'last_name', 
        'patronymic_name', 
        'phone_number', 
        'mac_address', 
        'phone_model', 
        'company',
        'line',
        'atc',
        'date_added', 
        'update_added', 
        'active'
        ) 

    for col_num in range(len(columns)): 
        ws.write(row_num,col_num,columns[col_num], font_style)
    
    rows = Lead.objects.filter().values_list(
        'first_name', 
        'last_name', 
        'patronymic_name', 
        'phone_number', 
        'mac_address', 
        'phone_model', 
        'company', 
        'line',
        'atc',
        'date_added', 
        'update_added', 
        'active'
        )

    for row in rows:
        row_list = list (row)
        row_list[3] = Number.objects.get(pk=row_list[3])
        row_list[5] = Apparats.objects.get(pk=row_list[5])
        row_list[6] = Company.objects.get(pk=row_list[6])
        row=tuple(row_list)
        row_num += 1

        for col_num in range(len(row)):
            ws.write(row_num,col_num,str(row[col_num]))
    wb.save(response)

    return response


class SignupView(generic.CreateView):
    template_name = "registration/signup.html"
    form_class = CustomUserCreationForm

    def get_success_url(self):
        return reverse("login")


class LandingPageView(generic.TemplateView):
    template_name = "landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("/leads")
        return super().dispatch(request, *args, **kwargs)



def landing_page(request):
    return render(request, "landing.html")


def lead_list(request):
    search_number_query = request.GET.get('number', '',)
    search_mac_query = request.GET.get('mac', '',)
    search_name_query = request.GET.get('name', '', )
        
    if search_number_query:
        leads = Lead.objects.filter(phone_number__in=Number.objects.filter(name__icontains=search_number_query))
    elif search_mac_query:
        leads = Lead.objects.filter(mac_address__icontains=search_mac_query)
    elif search_name_query:
        leads = Lead.objects.filter(last_name__icontains=search_name_query)

    else:
        leads = Lead.objects.all()

    context = {
        "leads": leads
    }
    return render(request, "leads/lead_list.html", context)

# def lead_list(request):
#     leads = Lead.objects.all()

#     results = []

#     if request.method == "GET":

#         query = request.GET.get('search')

#         if query == '':

#             query = 'None'
        
#         results = Lead.objects.all()

#     context = {
#         "leads": leads,
#         "query": query,
#         "results": results
#     }
#     return render(request, "leads/lead_list.html", context)


def lead_detail(request, pk):
    lead = Lead.objects.get(id=pk)
    context = {
        "lead": lead
    }
    return render(request, "leads/lead_detail.html", context)


def lead_create(request):
    form = LeadCreateModelForm()
    if request.method == "POST":
        form = LeadCreateModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("/leads")
    context = {
        "form": form
    }
    return render(request, "leads/lead_create.html", context)


def lead_update(request, pk):
    lead = Lead.objects.get(id=pk)
    form = LeadModelForm(instance=lead)
    if request.method == "POST":
        form = LeadModelForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            return redirect("/leads")
    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/lead_update.html", context)


class LeadDeleteView(OrganisorAndLoginRequiredMixin, generic.DeleteView):
    template_name = "leads/lead_delete.html"

    def get_success_url(self):
        return reverse("leads:lead-list")

    def get_queryset(self):
        user = self.request.user
        return Lead.objects.all()


# COMPANY COMPANY COMPANY COMPANY COMPANY

def company_list(request):
    leads = Company.objects.all()
    context = {
        "leads": leads
    }
    return render(request, "leads/company.html", context)


def company_detail(request, pk):
    lead = Company.objects.get(id=pk)
    context = {
        "lead": lead,
    }
    return render(request, "leads/company_detail.html", context)


def company_create(request):
    form = CompanyModelForm()
    if request.method == "POST":
        form = CompanyModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("company")

        else:
            return redirect("company")    
    context = {
        "form": form
    }
    return render(request, "leads/company_create.html", context)


def company_update(request, pk):
    company = Company.objects.get(id=pk)
    form = CompanyModelForm(instance=company)
    if request.method == "POST":
        form = CompanyModelForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect("company")
    context = {
        "form": form,
        "company": company
    }
    return render(request, "leads/company_update.html", context)


class CompanyDeleteView(OrganisorAndLoginRequiredMixin, generic.DeleteView):
    template_name = "leads/company_delete.html"

    def get_success_url(self):
        return reverse("company")

    def get_queryset(self):
        user = self.request.user
        return Company.objects.all()


# APPRAT APPRAT APPRAT APPRAT APPRAT APPRAT


def apparat_list(request):
    leads = Apparats.objects.all()
    context = {
        "leads": leads
    }
    return render(request, "leads/apparats.html", context)


def apparat_create(request):
    form = ApparatModelForm()
    if request.method == "POST":
        form = ApparatModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("apparats")
    context = {
        "form": form
    }
    return render(request, "leads/apparats_create.html", context)


def apparat_list(request):
    leads = Apparats.objects.all()
    context = {
        "leads": leads
    }
    return render(request, "leads/apparats.html", context)


def apparat_detail(request, pk):
    lead = Apparats.objects.get(id=pk)
    context = {
        "lead": lead
    }
    return render(request, "leads/apparats_detail.html", context)


def apparat_update(request, pk):
    lead = Apparats.objects.get(id=pk)
    form = ApparatModelForm(instance=lead)
    if request.method == "POST":
        form = ApparatModelForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            return redirect("apparats")
    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/apparats_update.html", context)


class ApparatDeleteView(OrganisorAndLoginRequiredMixin, generic.DeleteView):
    template_name = "leads/apparats_delete.html"

    def get_success_url(self):
        return reverse("apparats")

    def get_queryset(self):
        user = self.request.user
        return Apparats.objects.all()


# NUMBER NUMBER NUMBER NUMBER


def number_list(request):
    leads = Number.objects.all()
    context = {
        "leads": leads
    }
    return render(request, "leads/number.html", context)


def number_detail(request, pk):
    number = Number.objects.get(id=pk)
    context = {
        "number": number
    }
    return render(request, "leads/lead_detail.html", context)


def number_create(request):
    form = NumberModelForm()
    if request.method == "POST":
        form = NumberModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("number")
    context = {
        "form": form
    }
    return render(request, "leads/lead_create.html", context)


class NumberDeleteView(OrganisorAndLoginRequiredMixin, generic.DeleteView):
    template_name = "leads/number_delete.html"

    def get_success_url(self):
        return reverse("number")

    def get_queryset(self):
        user = self.request.user
        return Number.objects.all()



class LeadJsonView(generic.View):

    def get(self, request, *args, **kwargs):
        
        qs = list(Lead.objects.all().values(
            "first_name", 
            "last_name", 
            "age")
        )

        return JsonResponse({
            "qs": qs,
        })
