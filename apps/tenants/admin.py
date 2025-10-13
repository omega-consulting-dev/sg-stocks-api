from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from apps.tenants.models import Company, Domain


@admin.register(Company)
class CompanyAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'schema_name', 'plan', 'is_active', 'created_on']
    list_filter = ['plan', 'is_active', 'created_on']
    search_fields = ['name', 'schema_name', 'email']


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain']