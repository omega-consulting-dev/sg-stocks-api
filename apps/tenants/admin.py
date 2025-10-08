from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from apps.tenants.models import Company

@admin.register(Company)
class CompanyAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'schema_name')