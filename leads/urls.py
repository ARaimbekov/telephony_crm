
from django.urls import path
from .views import *

app_name = "leads"

urlpatterns = [
    path('', lead_list, name='lead-list'),
    path('json/', LeadJsonView.as_view(), name='lead-list-json'),
    path('<int:pk>/', lead_detail, name='lead-detail'),
    path('<int:pk>/update/', lead_update, name='lead-update'),
    path('<int:pk>/delete/', lead_delete, name='lead-delete'),
    path('create/', lead_create, name='lead-create'),
    # path('phones/', phones, name='phones'),
    path('phone/', phone_number, name='lead-phone'),
    path('phone_create/', phone_number_create, name='lead-phone-create'),
    path('users/', user_list, name='users'),
    path('<int:pk>/user_update/', user_update, name='user_update'),
    path("<int:pk>/password_change/", password_change, name="password_change"),
    path('<int:pk>/user_delete/', user_delete, name='user_delete'),

    # path('<int:pk>/', CompanyDetailView.as_view(), name='company_detail'),
    path('create_company/', company_create, name='company_create'),
    path('<int:pk>/company_update/', company_update, name='company_update'),
    path('<int:pk>/company_delete/', company_delete, name='company_delete'),

    path('apparats_create/', apparat_create, name='apparats_create'),
    path('<int:pk>/apparats_update/', apparat_update, name='apparats_update'),
    path('<int:pk>/apparats_delete/', apparat_delete, name='apparats_delete'),

    path('atc_create/', atc_create, name='atc_create'),
    path('<int:pk>/atc_update/', atc_update, name='atc_update'),
    path('<int:pk>/atc_delete/', atc_delete, name='atc_delete'),

    path('create-number/', number_create, name='number-create'),
    path('<int:pk>/number_delete/', number_delete, name='number_delete'),
    # path('find-number/', number_list, name='number-find'),

    path('export_table/', export_to_csv, name='export_table'),
    path('export_to_exel/', export_to_exel, name='export_table_exel'),
]