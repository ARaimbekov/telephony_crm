
from django.urls import path
from .views import (
    LeadListView, LeadDetailView, LeadCreateView, LeadUpdateView, LeadDeleteView,
    AssignAgentView, CategoryListView, CategoryDetailView, LeadCategoryUpdateView,
    CategoryCreateView, CategoryUpdateView, CategoryDeleteView, LeadJsonView, CompanyUpdateView, CompanyDetailView, ApparatUpdateView, CompanyDeleteView,
    FollowUpCreateView, FollowUpUpdateView, FollowUpDeleteView, CompanyListView, CompanyCreateView, ApparatCreateView, NumberCreateView, export_to_csv, ApparatDeleteView
)

app_name = "leads"

urlpatterns = [
    path('', LeadListView.as_view(), name='lead-list'),
    path('json/', LeadJsonView.as_view(), name='lead-list-json'),
    path('<int:pk>/', LeadDetailView.as_view(), name='lead-detail'),
    path('<int:pk>/update/', LeadUpdateView.as_view(), name='lead-update'),
    path('<int:pk>/delete/', LeadDeleteView.as_view(), name='lead-delete'),
    path('<int:pk>/assign-agent/', AssignAgentView.as_view(), name='assign-agent'),
    path('<int:pk>/category/', LeadCategoryUpdateView.as_view(), name='lead-category-update'),
    path('<int:pk>/followups/create/', FollowUpCreateView.as_view(), name='lead-followup-create'),
    path('followups/<int:pk>/', FollowUpUpdateView.as_view(), name='lead-followup-update'),
    path('followups/<int:pk>/delete/', FollowUpDeleteView.as_view(), name='lead-followup-delete'),
    path('create/', LeadCreateView.as_view(), name='lead-create'),

    # path('<int:pk>/', CompanyDetailView.as_view(), name='company_detail'),
    path('create_company/', CompanyCreateView.as_view(), name='company_create'),
    path('<int:pk>/company_update/', CompanyUpdateView.as_view(), name='company_update'),
    path('<int:pk>/company_delete/', CompanyDeleteView.as_view(), name='company_delete'),


    path('apparats_create/', ApparatCreateView.as_view(), name='apparats_create'),
    path('<int:pk>/apparats_update/', ApparatUpdateView.as_view(), name='apparats_update'),
    path('<int:pk>/apparats_delete/', ApparatDeleteView.as_view(), name='apparats_delete'),

    path('create-number/', NumberCreateView.as_view(), name='number-create'),

    path('export_table/', export_to_csv, name='export_table'),

    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<int:pk>/update/', CategoryUpdateView.as_view(), name='category-update'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category-delete'),
    path('create-category/', CategoryCreateView.as_view(), name='category-create'),

]