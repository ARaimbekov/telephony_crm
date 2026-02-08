from django.contrib import admin
from .models import Lead, Company, Apparats, Number, Atc, User, EmployeeDwh

admin.site.register(User)

@admin.register(EmployeeDwh)
class EmployeeDwhAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "samaccountname",
        "mail",
        "company",
        "department",
        "job_title",
        "status",
        "source_last_seen_at",
        "updated_at",
    )
    list_filter = ("status", "company", "department")
    search_fields = ("full_name", "samaccountname", "mail", "company", "department", "job_title")
    ordering = ("-updated_at",)
    readonly_fields = ("updated_at", "source_last_seen_at", "deleted_at")

    # чтобы случайно руками не ломали синхронизацию
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False