from django.contrib import admin
from apps.services.models import Service, ServiceCategory, ServiceIntervention

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['reference', 'name', 'category', 'unit_price', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'reference']
    filter_horizontal = ['assigned_staff']


@admin.register(ServiceIntervention)
class ServiceInterventionAdmin(admin.ModelAdmin):
    list_display = ['service', 'customer', 'scheduled_date', 'status', 'assigned_to']
    list_filter = ['status', 'scheduled_date']
    search_fields = ['service__name', 'customer__username']
