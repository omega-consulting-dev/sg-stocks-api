"""
Product admin configuration.
"""

from django.contrib import admin
from apps.products.models import Product, ProductCategory, ProductImage


class ProductImageInline(admin.TabularInline):
    """Inline for product images."""
    model = ProductImage
    extra = 1
    fields = ['image', 'is_primary', 'order']


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    """Admin for ProductCategory model."""
    
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'description', 'parent')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin for Product model."""
    
    list_display = [
        'reference', 'name', 'category', 'selling_price',
        'cost_price', 'is_for_sale', 'is_active', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_for_sale', 'product_type',
        'category', 'created_at'
    ]
    search_fields = ['name', 'reference', 'barcode', 'description']
    ordering = ['-created_at']
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': (
                'reference', 'barcode', 'name', 'description', 'category'
            )
        }),
        ('Prix', {
            'fields': ('cost_price', 'selling_price', 'tax_rate')
        }),
        ('Stock', {
            'fields': ('minimum_stock', 'optimal_stock', 'product_type')
        }),
        ('Caractéristiques', {
            'fields': ('weight', 'volume'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_for_sale', 'is_for_purchase', 'is_active')
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        """Save model and set created_by/updated_by."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)