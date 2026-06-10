import csv
import re
import xlwt
import logging
import datetime
from django import contrib
import random
import string
import json
import requests
import shortuuid
from django.contrib.auth.views import PasswordResetDoneView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http.response import JsonResponse
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import generic
from agents.mixins import OrganisorAndLoginRequiredMixin
from .models import Lead, Company, Apparats, Number, Atc, User, EmployeeDwh, ApiToken
from .forms import *
from django.db.models import ProtectedError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from django.core.files.uploadedfile import UploadedFile 
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from django.utils.timezone import now
import tempfile
import os
from django.db import transaction
from django.db.models import Prefetch
from functools import wraps


from .migrations_utils import migrate_numbers, migrate_mac, change_atc



logger = logging.getLogger(__name__)

def employee_search(request):
    q = (request.GET.get("q") or "").strip()
    qs = EmployeeDwh.objects.filter(status=EmployeeDwh.Status.ACTIVE)

    if q:
        qs = qs.filter(
            Q(full_name__icontains=q) |
            Q(mail__icontains=q) |
            Q(company__icontains=q) |
            Q(department__icontains=q) |
            Q(job_title__icontains=q) |
            Q(samaccountname__icontains=q)
        )

    qs = qs.order_by("full_name")[:25]

    results = []
    for e in qs:
        text = f"{e.full_name} — {e.company or 'Без компании'}"
        results.append({"id": e.id, "text": text})

    return JsonResponse({"results": results})


def _save_upload_to_temp(upload: UploadedFile) -> str:
    suffix = f"_{now().strftime('%Y%m%d_%H%M%S')}.csv"
    fd, path = tempfile.mkstemp(prefix="upload_", suffix=suffix)
    with os.fdopen(fd, 'wb') as dst:
        for chunk in upload.chunks():
            dst.write(chunk)
    return path

def _staff_check(user):
    return user.is_authenticated and user.is_staff


def export_to_csv(request):
    leads = Lead.objects.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=profile_export.csv'
    
    # Создаем объект writer для записи CSV
    writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    # Заголовки столбцов
    writer.writerow([
        'first_name',
        'last_name',
        'patronymic_name',
        'phone_number',
        'mac_address',
        'phone_model',
        'company',
        'line',
        'atc_name',
        'atc_ip',
        'date_added',
        'update_added',
        'active',
        'passwd',
        'reservation',
        'record_calls',
        'external_line_access',
        'call_forwarding',
        'timezone',
    ])

    # Получаем данные из базы
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
        'atc',
        'date_added',
        'update_added',
        'active',
        'passwd',
        'reservation',
        'record_calls',
        'external_line_access',
        'call_forwarding',
        'timezone',
    )

    # Обработка каждой строки
    for row in rows:
        row_list = list(row)
        
        # Преобразуем связанные объекты
        row_list[3] = Number.objects.get(pk=row_list[3])  # phone_number
        row_list[5] = Apparats.objects.get(pk=row_list[5])  # phone_model
        row_list[6] = Company.objects.get(pk=row_list[6])  # company
        
        # Получаем IP-адрес ATC
        ip_addr = Atc.objects.filter(pk=row_list[8]).values('ip_address')
        address = ""
        for i in ip_addr:
            address = i['ip_address']
        row_list[9] = address  # atc_ip
        row_list[8] = Atc.objects.get(pk=row_list[8])  # atc_name
        
        # Убираем кавычки для timezone
        if row_list[18]:  # timezone
            row_list[18] = str(row_list[18])  # Просто преобразуем в строку без кавычек

        # Записываем строку в CSV
        writer.writerow(row_list)

    return response


def export_to_exel(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Expenses' + \
        str(datetime.datetime.now())+'.xls'
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
        'atc_name',
        'atc_ip',
        'date_added',
        'update_added',
        'active',
        'record_calls',
        'external_line_access',
        'call_forwarding',
        'timezone',
    )

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

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
        'atc',
        'date_added',
        'update_added',
        'active',
        'record_calls',
        'external_line_access',
        'call_forwarding',
        'timezone',
    )

    for row in rows:
        row_list = list(row)
        row_list[3] = Number.objects.get(pk=row_list[3])
        row_list[5] = Apparats.objects.get(pk=row_list[5])
        row_list[6] = Company.objects.get(pk=row_list[6])
        ip_addr = Atc.objects.filter(pk=row_list[8]).values('ip_address')
        for i in ip_addr:
            address = (i['ip_address'])

        row_list[9] = address
        row_list[8] = Atc.objects.get(pk=row_list[8])


        row = tuple(row_list)
        row_num += 1

        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]))
    wb.save(response)

    return response


class SignupView(generic.CreateView):
    template_name = "registration/signup.html"
    form_class = CustomUserCreationForm

    def get_success_url(self):
        return reverse("leads:users")


@login_required
class LandingPageView(generic.TemplateView):
    template_name = "landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("/leads")
        return super().dispatch(request, *args, **kwargs)


@login_required
def landing_page(request):
    return render(request, "landing.html")


@login_required
def user_list(request):
    leads = User.objects.filter(is_active=True)
    context = {
        "leads": leads
    }
    return render(request, "leads/users.html", context)


@login_required
def user_update(request, pk):
    lead = User.objects.get(id=pk)
    form = UserModelForm(instance=lead)
    if request.method == "POST":
        form = UserModelForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            messages.success(request, "Изменения были удачно внесены !")
            return redirect("leads:users")
    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/user_update.html", context)


@login_required
def user_delete(request, pk):
    lead = User.objects.get(id=pk)
    form = UserDelModelForm(instance=lead)
    if request.method == "POST":
        # user_id = request.POST['username']   
        form = UserDelModelForm(request.POST, instance=lead)
        try:
            if form.is_valid():
                lead.is_active = False
                lead.save()
                messages.success(request, "Пользователь был успешно удален !")
                return redirect("leads:users")
        except Exception as e:
            return redirect("error")

    context = {
        "form": form,
        "lead": lead,
    }
    return render(request, "leads/user_delete.html", context)


@login_required
def password_change(request, pk):
    user = User.objects.get(id=pk)
    form = SetPasswordForm(user)
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Пароль был успешно изменён !")
            return redirect('leads:users')
        else:
            for error in list(form.errors.values()):
                messages.error(request, error)
    context = {
        "form": form,
        "user": user
    }
    return render(request, "leads/password_reset_confirm.html", context)


# LEAD LEAD LEAD LEAD LEAD
@login_required
def lead_list(request):
    context = {}
    search_number_query = request.GET.get('number', '')
    search_mac_query = request.GET.get('mac', '')
    search_name_query = request.GET.get('name', '')
    search_record_calls = request.GET.get('record_calls', '')
    search_external_line_access = request.GET.get('external_line_access', '')
    search_call_forwarding = request.GET.get('call_forwarding', '')
    page_list = request.GET.get('page')

    leads = Lead.objects.prefetch_related("atc", "phone_model", "company", "employees").all()

    # Фильтрация по существующим полям
    if search_number_query:
        leads = leads.filter(phone_number__name__icontains=search_number_query)
    if search_mac_query:
        leads = leads.filter(mac_address__icontains=search_mac_query)
    if search_name_query:
        leads = leads.filter(
            Q(last_name__icontains=search_name_query) |
            Q(first_name__icontains=search_name_query) |
            Q(patronymic_name__icontains=search_name_query) |
            Q(display_name__icontains=search_name_query) |
            Q(employees__full_name__icontains=search_name_query)
        ).distinct()


    # Фильтрация по новым полям
    if search_record_calls:
        leads = leads.filter(record_calls=(search_record_calls == "true"))
    if search_external_line_access:
        leads = leads.filter(external_line_access=search_external_line_access)
    if search_call_forwarding:
        leads = leads.filter(call_forwarding__icontains=search_call_forwarding)

    # Пагинация
    paginator = Paginator(leads, 15)

    try:
        page = paginator.page(page_list)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    # Дополнительные данные для контекста
    reserved_number = Lead.objects.filter(reservation=True).count()
    total_number = Lead.objects.count()
    free_number = Number.objects.count() - total_number
    all_number = Number.objects.count()
    all_atc = Atc.objects.count()

    context = {
        "page": page,
        "total_number": total_number,
        "reserved_number": reserved_number,
        "free_number": free_number,
        "all_number": all_number,
        "all_atc": all_atc,
    }

    return render(request, "leads/lead_list.html", context)


@login_required
def lead_detail(request, pk):
    lead = get_object_or_404(
        Lead.objects.prefetch_related(
            "atc",
            "phone_model",
            "company",
            Prefetch(
                "employees",
                queryset=EmployeeDwh.objects.filter(status=EmployeeDwh.Status.ACTIVE).prefetch_related(
                    Prefetch(
                        "leads",
                        queryset=Lead.objects.select_related("phone_number").only("id", "phone_number", "line", "active")
                    )
                ),
            ),
        ),
        id=pk
    )

    phone = str(lead.phone_number)

    try:
        res = requests.get(f'http://10.90.42.250:8084/phoneinfo?phone={phone}', timeout=5)
        res.raise_for_status()
        res_json = res.json()
    except requests.RequestException as e:
        res_json = {}
        api_error = f"Ошибка при получении данных из API: {e}"
    else:
        api_error = None

    atc_ip_api = res_json.get('ipaddr', 'Неизвестно')
    user_agent = res_json.get('useragent', 'Неизвестно')
    soket_info = res_json.get('socketinfo', {}) or {}
    status = res_json.get('status', 'Неизвестно')
    mac = soket_info.get('mac', 'Неизвестно')
    switch_ip = soket_info.get('ipaddr', 'Неизвестно')
    port = soket_info.get('port', 'Неизвестно')
    cabinet = soket_info.get('cabinet', 'Неизвестно')
    socket = soket_info.get('socket', 'Неизвестно')
    description = soket_info.get('description', 'Неизвестно')

    # список сотрудников + все их номера
    employee_cards = []
    for emp in lead.employees.all():
        employee_cards.append({
            "emp": emp,
            "leads": emp.leads.select_related("phone_number").all()
        })

    context = {
        "lead": lead,
        "error": api_error,

        "atc_ip_api": atc_ip_api,
        "useragent": user_agent,
        "switch_ip": switch_ip,
        "status": status,
        "port": port,
        "cabinet": cabinet,
        "socket": socket,
        "description": description,
        "mac": mac,

        "record_calls": lead.record_calls,
        "external_line_access": lead.get_external_line_access_display(),
        "call_forwarding": lead.call_forwarding or "Не указано",

        "employee_cards": employee_cards,
    }

    return render(request, "leads/lead_detail.html", context)


@login_required
def lead_create(request):
    form = LeadCreateModelForm()

    if request.method == "POST":
        try:
            form = LeadCreateModelForm(request.POST)
            pattern = re.compile("^([0-9A-Fa-f]{2}[:-]{0,1}){5}([0-9A-Fa-f]{2})$")
            if pattern.match(request.POST['mac_address']) or request.POST['mac_address'] == '':
                if form.is_valid():
                    if ('reservation') in request.POST:
                        letters = string.digits
                        new_mac = '000000' + \
                            ''.join(random.choice(letters) for i in range(6))
                        temp = request.POST.copy()
                        temp['mac_address'] = new_mac
                        temp['created_user'] = request.user.username
                        request.POST = temp
                        form = LeadCreateModelForm(request.POST)
                        form.save()
                        messages.success(request, "Вы успешно создали зарезервированную позицию !")
                        return redirect("/leads")
                    elif "-" in request.POST["mac_address"]:
                        temp = request.POST.copy()
                        mac = temp['mac_address']
                        result = ''
                        for i in mac.split("-"):
                            result += '' + i
                        result = result.lower()
                        temp['mac_address'] = result
                        temp['created_user'] = request.user.username
                        request.POST = temp
                        form = LeadCreateModelForm(request.POST)
                        form.save()
                        messages.success(request, "Вы успешно создали зарезервированную позицию !")
                        return redirect("/leads")
                    elif ":" in request.POST["mac_address"]:
                        temp = request.POST.copy()
                        mac = temp['mac_address']
                        result = ''
                        for i in mac.split(":"):
                            result += '' + i
                        result = result.lower()
                        temp['mac_address'] = result
                        temp['created_user'] = request.user.username
                        request.POST = temp
                        form = LeadCreateModelForm(request.POST)
                        form.save()
                        messages.success(request, "Вы успешно создали зарезервированную позицию !")
                        return redirect("/leads")
                    elif "." in request.POST["mac_address"]:
                        temp = request.POST.copy()
                        mac = temp['mac_address']
                        result = ''
                        for i in mac.split("."):
                            result += '' + i
                        result = result.lower()
                        temp['mac_address'] = result
                        temp['created_user'] = request.user.username
                        request.POST = temp
                        form = LeadCreateModelForm(request.POST)
                        form.save()
                        messages.success(request, "Вы успешно создали зарезервированную позицию !")
                        return redirect("/leads")             
                    elif not request.POST["mac_address"]:
                        return render(request, "error_mac.html")
                    else:
                        temp = request.POST.copy()
                        mac = temp['mac_address']
                        mac = mac.lower()
                        temp['mac_address'] = mac
                        temp['created_user'] = request.user.username
                        request.POST = temp
                        form = LeadCreateModelForm(request.POST)
                        form.save()
                        messages.success(request, "Вы успешно создали позицию, настройки будут применены в течении 10 минут !")
                        return redirect("/leads")
                else:
                    print("FORM ERRORS:", form.errors)
                    print("NON FIELD ERRORS:", form.non_field_errors())
                    return render(request, "error_mac_failed.html")
                    # return render(request, "error_mac_failed.html")
            else:
                return render(request, "error_mac_type_failed.html")
        except Exception as e:
            number_on_mac = request.POST["mac_address"]
            print(number_on_mac)
            # number_on_mac = Lead.objects.filter(mac_address__icontains='number_on_mac')
            # leads = Lead.objects.filter(phone_number__in=Number.objects.filter(name__icontains=search_number_query))
            mac = Lead.objects.filter(mac_address__icontains=number_on_mac)
            print(mac)
            context = {
                'error': 'Такой MAC адрес уже существует',
                'mac' : mac,

            }
            return render(request, "error.html", context)

    context = {
        "form": form,
    }
    return render(request, "leads/lead_create.html", context)


@login_required    
def phone_number_create(request):
    data = json.loads(request.body)
    print(data)
    atc_id = data.get("id")
    if atc_id is None:
        return JsonResponse({"error": "Missing 'id' parameter"}, status=400)
    numbers = Lead.objects.all().values('phone_number')
    phone_number = Number.objects.filter(atc__id=atc_id).exclude(id__in=numbers)
    return JsonResponse(list(phone_number.values("id", "name")), safe=False)


@login_required    
def phone_number(request):
    data = json.loads(request.body)
    atc_id = data["id"]
    atc_name = data['atc_name']
    current_number = data['current_number']
    if not atc_id:
        atc_id = Atc.objects.filter(name=atc_name).first().id
    numbers = Lead.objects.all().values('phone_number')
    current_number = Number.objects.filter(name=current_number)
    number_id = Number.objects.filter(atc_id=atc_id)
    if set(current_number).intersection(set(number_id)):
        phone_number = Number.objects.filter(atc__id=atc_id).exclude(id__in=numbers).union(current_number)
        print('СССС текущим', phone_number)
        return JsonResponse(list(phone_number.values("id", "name")), safe=False)
    
    phone_number = Number.objects.filter(atc__id=atc_id).exclude(id__in=numbers)
    return JsonResponse(list(phone_number.values("id", "name")), safe=False)


@login_required
def lead_update(request, pk):
    lead = Lead.objects.get(id=pk)
    
    # Безопасно получаем связанные объекты (с fallback если их нет)
    try:
        company = lead.company.first()
    except:
        company = None
    
    try:
        model = lead.phone_model.first()
    except:
        model = None
    
    try:
        atc = lead.atc.first()
    except:
        atc = None
    
    updated_user = request.user.username
    my_number = lead.phone_number
    my_num_obj = Number.objects.filter(name=my_number).all()
    numbers = Lead.objects.all().values('phone_number')
    current_mac = lead.mac_address

    initial_dict = {}
    if atc:
        initial_dict['atc'] = atc
    if model:
        initial_dict['phone_model'] = model
    if company:
        initial_dict['company'] = company
    
    form = LeadModelForm(instance=lead, initial=initial_dict)
    
    if atc:
        form.fields['phone_number'].queryset = Number.objects.filter(atc__id=atc.id).exclude(id__in=numbers).all().union(my_num_obj)
    else:
        form.fields['phone_number'].queryset = my_num_obj

    if request.method == "POST":
        form = LeadModelForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            lead.updated_user = updated_user
            lead.mac_address = lead.mac_address.lower()
            print(lead.mac_address)
            # Обновить пароль, если MAC-адрес обновлен
            if current_mac != lead.mac_address:
                print('HAHAHAHA')
                lead.passwd = shortuuid.uuid()

            lead.save()
            messages.success(request, "В течении 10 минут изменения будут применены !")
            return redirect("/leads")

    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/lead_update.html", context)


@login_required
def lead_delete(request, pk):
    lead = Lead.objects.get(id=pk)
    form = LeadDelModelForm(instance=lead)
    if request.method == "POST":
        form = LeadDelModelForm(request.POST, instance=lead)
        try:
            if form.is_valid():
                lead.delete()
                messages.success(request, "Позиция была удалена !")
                return redirect("leads:lead-list")
        except Exception as e:
            return redirect("error")

    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/lead_delete.html", context)



# COMPANY COMPANY COMPANY COMPANY COMPANY

@login_required
def company_list(request):
    leads = Company.objects.all()
    context = {
        "leads": leads
    }
    return render(request, "leads/company.html", context)


@login_required
def company_detail(request, pk):
    lead = Company.objects.get(id=pk)
    context = {
        "lead": lead,
    }
    return render(request, "leads/company_detail.html", context)


@login_required
def company_create(request):
    form = CompanyModelForm()
    if request.method == "POST":
        form = CompanyModelForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                messages.success(request, "Создание компании прошло успешно !")
                return redirect("company")

        except Exception as e:
            context = {
                'error': "Создание невозможно, такая уже компания существует."
            }
            return render(request, "error.html", context)

    context = {
        "form": form
    }
    return render(request, "leads/company_create.html", context)


@login_required
def company_update(request, pk):
    company = Company.objects.get(id=pk)
    form = CompanyModelForm(instance=company)
    if request.method == "POST":
        form = CompanyModelForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Изменения были удачно внесены !")
            return redirect("company")
    context = {
        "form": form,
        "company": company
    }
    return render(request, "leads/company_update.html", context)


@login_required
def company_delete(request, pk):
    lead = Company.objects.get(id=pk)
    form = CompanyDelModelForm(instance=lead)
    if request.method == "POST":
        form = CompanyDelModelForm(request.POST, instance=lead)
        try:
            if form.is_valid():
                if not len(Lead.objects.filter(company=lead).all()):
                    lead.delete()
                    messages.success(request, "Компияния была удалена !")
                    return redirect("company")
                else:
                    return render(request, "error_company.html")
        
        
        except Exception as e:
            context = {
                'error': e
            }
            return render(request, "error.html", context)

    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/company_delete.html", context)


# APPRAT APPRAT APPRAT APPRAT APPRAT APPRAT


@login_required
def apparat_list(request):
    leads = Apparats.objects.all()
    context = {
        "leads": leads
    }
    return render(request, "leads/apparats.html", context)


@login_required
def apparat_create(request):
    form = ApparatModelForm()
    if request.method == "POST":
        form = ApparatModelForm(request.POST)
        try:    
            if form.is_valid():
                form.save()
                messages.success(request, "Модель телефона была успешна создана !")
                return redirect("apparats")

        except Exception as e:
            context = {
                'error': "Создание невозможно, такая модель телефона уже существует."
            }
            return render(request, "error.html", context)
        
    context = {
        "form": form
    }
    return render(request, "leads/apparats_create.html", context)


@login_required
def apparat_list(request):
    leads = Apparats.objects.all()
    context = {
        "leads": leads
    }
    return render(request, "leads/apparats.html", context)


@login_required
def apparat_detail(request, pk):
    lead = Apparats.objects.get(id=pk)
    context = {
        "lead": lead
    }
    return render(request, "leads/apparats_detail.html", context)


@login_required
def apparat_update(request, pk):
    lead = Apparats.objects.get(id=pk)
    form = ApparatModelForm(instance=lead)
    if request.method == "POST":
        form = ApparatModelForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            messages.success = (request, "Изменения были удачно внесены !")
            return redirect("apparats")
    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/apparats_update.html", context)


@login_required
def apparat_delete(request, pk):
    lead = Apparats.objects.get(id=pk)
    form = ApparatDelModelForm(instance=lead)
    if request.method == "POST":
        form = ApparatDelModelForm(request.POST, instance=lead) 
        try:
            if form.is_valid():
                if not len(Lead.objects.filter(phone_model=lead).all()):
                    lead.delete()
                    messages.success(request, "Модель телефона была удалена !")
                    return redirect("apparats")
                else:
                    return render(request, "error_model.html")

        except Exception as e:
            context = {
                'error': e
            }
            return render(request, "error.html", context)

    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/apparats_delete.html", context)


# NUMBER NUMBER NUMBER NUMBER

@login_required
def number_list(request):
    context={}
    number_query = request.GET.get('number','',)
    page_list = request.GET.get('page')

    if number_query:
        leads = Number.objects.filter(name__icontains=number_query)
        context['leads'] = leads
    
    else:
        leads = Number.objects.order_by('name')
        context["leads"] = leads

    paginator = Paginator(leads, 15)
        
    try:
        page = paginator.page(page_list)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    context['page'] = page

    return render(request, "leads/number.html", context)


@login_required
def number_detail(request, pk):
    number = Number.objects.get(id=pk)
    context = {
        "number": number
    }
    return render(request, "leads/lead_detail.html", context)


@login_required
def number_create(request):
    form = NumberModelForm()
    if request.method == "POST":
        form = NumberModelForm(request.POST)
        atc = Atc.objects.filter(pk=request.POST["atc"]).first()
        try:
            if form.is_valid():
                if "-" in request.POST["name"]:
                    num1, num2 = [int(i)
                                for i in request.POST["name"].split('-')]
                           
                    for i in range(num1, num2+1):
                        number_list = Number.objects.filter().values_list('name', flat=True)

                        if i not in number_list:
                            try:
                                Number.objects.create(name=i, atc=atc).save()
                            
                            except IntegrityError as my_Except:
                                pass                

                    messages.success(request, "Номера телефонов были успешно внесены !")    
                    return redirect("number")
                elif " " in request.POST["name"]:
                    num = [int(i) for i in request.POST["name"].split()]
                    for i in num:
                        number_list = Number.objects.filter().values_list('name', flat=True)
                        if i not in number_list:
                            try:
                                Number.objects.create(name=i, atc=atc).save()
                            
                            except IntegrityError as my_Except:
                                pass                        
                    
                    messages.success(request, "Номера телефонов были успешно внесены !")
                    return redirect("number")
                elif "," in request.POST["name"]:
                    num = [int(i) for i in request.POST["name"].split(',')]
                    for i in num:
                        number_list = Number.objects.filter().values_list('name', flat=True)
                        if i not in number_list:
                            try:
                                Number.objects.create(name=i, atc=atc).save()
                            
                            except IntegrityError as my_Except:
                                pass  

                    messages.success(request, "Номера телефонов были успешно внесены !")
                    return redirect("number")
                else:
                    form.save()
                    messages.success(request, "Номер телефона был успешно внесен !")
                    return redirect("number")


        except Exception as e:
            e = 'Данный номер уже существует'
            context = {"error": e }
            return render(request, "error.html", context)

    context = {
        "form": form
    }
    return render(request, "leads/number_create.html", context)


@login_required
def number_delete(request, pk):
    lead = Number.objects.get(id=pk)
    form = NumberDelModelForm(instance=lead)
    if request.method == "POST":
        form = NumberDelModelForm(request.POST, instance=lead) 
        try:
            if form.is_valid():
                lead.delete()
                messages.success(request, "Номер телефона был удален !")
                return redirect("number")
            else:
                return render(request, 'error_number.html')

        except Exception as e:
            return render(request, "error_number.html")

    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/number_delete.html", context)

# ATC ATC ATC ATC ATC ATC

@login_required
def atc_list(request):
    leads = Atc.objects.all()
    context = {
        "leads": leads
    }
    return render(request, "leads/atc.html", context)


@login_required
def atc_detail(request, pk):
    lead = Atc.objects.get(id=pk)
    context = {
        "lead": lead
    }
    return render(request, "leads/atc_detail.html", context)


@login_required
def atc_create(request):
    form = AtcModelForm()
    if request.method == "POST":
        form = AtcModelForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                messages.success(request, "ATC была успешно создана !")
                return redirect("atc")
        except Exception as e:
            return redirect("error")
    context = {
        "form": form
    }
    return render(request, "leads/atc_create.html", context)


@login_required
def atc_update(request, pk):
    lead = Atc.objects.get(id=pk)
    form = AtcModelForm(instance=lead)
    if request.method == "POST":
        form = AtcModelForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            messages.success(request, "Изменения были удачно внесены ! ")
            return redirect("atc")
    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/atc_update.html", context)


@login_required
def atc_delete(request, pk):
    lead = Atc.objects.get(id=pk)
    form = AtcModelForm(instance=lead)
    if request.method == "POST":
        form = AtcModelForm(request.POST, instance=lead)
        try:
            if form.is_valid():
                lead.delete()
                messages.success(request, "ATC была удалена !")
                return redirect("atc")
        except Exception as e:
            return render(request, "error_atc.html")

    context = {
        "form": form,
        "lead": lead
    }
    return render(request, "leads/atc_delete.html", context)


def error_page(request):
    return render(request, "error.html")


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


def api_token_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        x_token = request.headers.get("X-API-Token", "")

        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "", 1).strip()
        elif x_token:
            token = x_token.strip()

        if not token:
            return JsonResponse(
                {"ok": False, "error": "missing api token"},
                status=401
            )

        token_obj = ApiToken.objects.filter(token=token, is_active=True).first()
        if not token_obj:
            return JsonResponse(
                {"ok": False, "error": "invalid api token"},
                status=403
            )

        request.api_token = token_obj
        return view_func(request, *args, **kwargs)

    return _wrapped


@csrf_exempt
@require_POST
@api_token_required
def api_migrate_numbers(request):
    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({"ok": False, "error": "missing file"}, status=400)

    temp_path = _save_upload_to_temp(upload)
    created, errors = 0, []

    with transaction.atomic():
        with open(temp_path, 'r', encoding='utf-8') as f:
            for raw in f:
                try:
                    parts = raw.split(';')
                    number = parts[1].strip()
                    atc_ip = parts[6].strip()
                    if number and atc_ip:
                        atc = Atc.objects.filter(ip_address=atc_ip).first()
                        Number.objects.create(name=number, atc=atc)
                        created += 1
                except Exception as e:
                    errors.append({"line": raw.strip(), "error": str(e)})

    os.remove(temp_path)
    return JsonResponse({"ok": True, "created": created, "errors": errors}, status=201)


@csrf_exempt
@require_POST
@api_token_required
def api_migrate_mac(request):
    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({"ok": False, "error": "missing file"}, status=400)

    company_name = request.POST.get('company_name')
    temp_path = _save_upload_to_temp(upload)

    created, reservations, errors = 0, 0, []
    with transaction.atomic():
        try:
            default_company = None
            if company_name:
                default_company = Company.objects.filter(name=company_name).first()
                if not default_company:
                    return JsonResponse({"ok": False, "error": f'company "{company_name}" not found'}, status=400)

            with open(temp_path, 'r', encoding='utf-8') as f:
                for raw in f:
                    try:
                        line = raw.strip().split(';')
                        if len(line) == 0:
                            continue
                        number = Number.objects.filter(name=line[1].strip()).first()
                        mac_address = line[2].strip().lower()
                        phone_line = line[4].strip()
                        password = line[5].strip()
                        atc_ip = line[6].strip()
                        full_name = line[7].strip()
                        atc = Atc.objects.filter(ip_address=atc_ip).first()

                        param = {
                            'phone_number': number,
                            'mac_address': mac_address,
                            'line': phone_line,
                            'reservation': False,
                            'passwd': password,
                            'updated_user': request.user.username,
                            'created_user': request.user.username,
                        }

                        if re.match(r'^\w*\s\w[.]\w[.]', full_name):
                            full_name_parts = full_name.split()
                            param['last_name'] = full_name_parts[0][:20]
                            _io = full_name_parts[1].split('.')
                            param['first_name'] = _io[0]
                            param['patronymic_name'] = _io[1]
                        else:
                            param['last_name'] = full_name[:20]

                        if len(mac_address) != 12 or mac_address == '000000000000':
                            param['reservation'] = True

                        mac_obj = Lead.objects.create(**param)
                        mac_obj.company.add(default_company if company_name else Company.objects.filter(name='OOO "ИНК"').first())
                        if atc:
                            mac_obj.atc.add(atc)

                        if param['reservation']:
                            letters = string.digits
                            while True:
                                try:
                                    new_mac = '000000' + ''.join(random.choice(letters) for _ in range(6))
                                    mac_obj.mac_address = new_mac
                                    mac_obj.phone_model.add(Apparats.objects.filter(name='Телефон_отсутствует').first())
                                    mac_obj.save()
                                    reservations += 1
                                    break
                                except Exception:
                                    pass
                        else:
                            mac_obj.phone_model.add(Apparats.objects.filter(name=line[3]).first())
                            mac_obj.save()

                        created += 1
                    except Exception as ie:
                        errors.append({"line": raw.strip(), "error": str(ie)})
        finally:
            os.remove(temp_path)

    return JsonResponse({"ok": True, "created": created, "reservations": reservations, "errors": errors}, status=201)


@csrf_exempt
@require_POST
@api_token_required
def api_change_atc(request):
    upload = request.FILES.get('file')
    atc_id = request.POST.get('atc_id')

    if not upload:
        return JsonResponse({"ok": False, "error": "missing file"}, status=400)
    if not atc_id or not atc_id.isdigit():
        return JsonResponse({"ok": False, "error": "invalid or missing atc_id"}, status=400)

    # читаем номера из файла
    content = upload.read().decode('utf-8', errors='ignore')
    raw_numbers = [ln.strip() for ln in content.splitlines() if ln.strip()]
    # на всякий: уберём всё, что не цифры/плюс/диез
    numbers = []
    for n in raw_numbers:
        n_norm = n.strip()
        # если там точка/запятая/пробел — оставим как есть, у тебя номера — простые (например "200")
        numbers.append(n_norm)

    try:
        atc = Atc.objects.get(pk=int(atc_id))
    except Atc.DoesNotExist:
        return JsonResponse({"ok": False, "error": f"ATC id={atc_id} not found"}, status=404)

    with transaction.atomic():
        # 1) обновляем atc у самих номеров
        updated_numbers = Number.objects.filter(name__in=numbers).update(atc=atc)

        # 2) у всех лидов, чьи номера попали в список, заменяем m2m atc на новую
        leads_qs = Lead.objects.select_for_update().filter(phone_number__name__in=numbers)
        changed_leads = 0
        for lead in leads_qs:
            # поведение как в твоём SQL: «заменить» связку на новую АТС
            lead.atc.set([atc])
            changed_leads += 1

    return JsonResponse({
        "ok": True,
        "updated_numbers": updated_numbers,
        "changed_leads": changed_leads,
        "target_atc_id": atc.id,
        "numbers_in_request": len(numbers)
    }, status=200)


def _staff_check(user):
    return user.is_authenticated and user.is_staff

@api_token_required
def api_atc_list(request):
    atcs = Atc.objects.all().values('id', 'name')
    return JsonResponse(list(atcs), safe=False)

@api_token_required
def api_export_full(request):
    """
    ВЫГРУЗКА: полный набор данных
    """
    qs = (
        Lead.objects
        .select_related("phone_number")
        .prefetch_related(
            "atc",
            "company",
            "phone_model",
            Prefetch(
                "employees",
                queryset=EmployeeDwh.objects.all().only(
                    "id", "guid_nsi", "full_name", "samaccountname",
                    "mail", "company", "department", "job_title", "status"
                )
            ),
        )
        .order_by("id")
    )

    data = []
    for lead in qs:
        data.append({
            "id": lead.id,
            "phone_number": str(lead.phone_number),  # Number.__str__ -> name
            "line": lead.line,
            "mac_address": lead.mac_address,
            "passwd": lead.passwd,
            "reservation": lead.reservation,
            "active": lead.active,

            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "patronymic_name": lead.patronymic_name,
            "display_name": lead.display_name,  # <-- твое новое поле

            "record_calls": lead.record_calls,
            "external_line_access": lead.external_line_access,
            "call_forwarding": lead.call_forwarding,
            "timezone": lead.timezone,

            "created_user": lead.created_user,
            "updated_user": lead.updated_user,
            "date_added": lead.date_added.isoformat() if lead.date_added else None,
            "update_added": lead.update_added.isoformat() if lead.update_added else None,

            "atc": [{"id": a.id, "name": a.name, "ip_address": a.ip_address} for a in lead.atc.all()],
            "company": [{"id": c.id, "name": c.name} for c in lead.company.all()],
            "phone_model": [{"id": p.id, "name": p.name} for p in lead.phone_model.all()],

            "employees": [{
                "id": e.id,
                "guid_nsi": str(e.guid_nsi),
                "full_name": e.full_name,
                "samaccountname": e.samaccountname,
                "mail": e.mail,
                "company": e.company,
                "department": e.department,
                "job_title": e.job_title,
                "status": e.status,
            } for e in lead.employees.all()],
        })

    return JsonResponse({"ok": True, "count": len(data), "results": data}, json_dumps_params={"ensure_ascii": False})


@api_token_required
def api_export_guid_number_display_name(request):
    """
    ВЫГРУЗКА: связка GUID - номер - ФИО
    (учитывает, что под одним номером может быть несколько сотрудников)
    """
    through = Lead.employees.through  # таблица связи Lead <-> EmployeeDwh

    qs = (
        through.objects
        .select_related("lead", "employeedwh", "lead__phone_number")
        .only(
            "lead__id",
            "lead__phone_number__name",
            "employeedwh__guid_nsi",
            "employeedwh__full_name",
        )
        .order_by("lead__id")
    )

    results = []
    for row in qs:
        results.append({
            "guid": str(row.employeedwh.guid_nsi),
            "number": row.lead.phone_number.name,
            "display_name": row.employeedwh.full_name or "",
            "lead_id": row.lead.id,
        })

    return JsonResponse({"ok": True, "count": len(results), "results": results}, json_dumps_params={"ensure_ascii": False})
