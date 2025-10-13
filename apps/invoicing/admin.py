from django.contrib import admin
from apps.invoicing.models import Invoice, InvoiceLine, InvoicePayment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1
    fields = ['description', 'quantity', 'unit_price', 'tax_rate', 'discount_percentage']


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0
    readonly_fields = ['payment_number', 'payment_date', 'amount', 'payment_method']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'customer', 'invoice_date', 'due_date',
        'total_amount', 'paid_amount', 'status', 'is_overdue'
    ]
    list_filter = ['status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'customer__username']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    inlines = [InvoiceLineInline, InvoicePaymentInline]
    ordering = ['-invoice_date']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('invoice_number', 'customer', 'sale', 'status')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date', 'payment_term')
        }),
        ('Montants', {
            'fields': ('subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'paid_amount')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'invoice', 'payment_date', 'amount', 'payment_method']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['payment_number', 'invoice__invoice_number']
    readonly_fields = ['payment_number', 'created_at']
    ordering = ['-payment_date']