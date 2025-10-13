from django.contrib import admin
from apps.sales.models import Sale, SaleLine, Quote, QuoteLine


class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 1
    fields = ['line_type', 'product', 'service', 'quantity', 'unit_price', 'tax_rate']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'customer', 'store', 'sale_date', 'total_amount', 'status', 'payment_status']
    list_filter = ['status', 'payment_status', 'sale_date', 'store']
    search_fields = ['sale_number', 'customer__username']
    readonly_fields = ['sale_number', 'created_at', 'updated_at', 'created_by', 'updated_by']
    inlines = [SaleLineInline]
    ordering = ['-sale_date']


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 1


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_number', 'customer', 'quote_date', 'valid_until', 'status', 'total_amount']
    list_filter = ['status', 'quote_date']
    search_fields = ['quote_number', 'customer__username']
    inlines = [QuoteLineInline]
    ordering = ['-quote_date']