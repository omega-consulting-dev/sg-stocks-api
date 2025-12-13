from django.contrib import admin

from apps.main.models import User 
from apps.main.models_settings import CompanySettings

class UserAdmin(admin.ModelAdmin):
    list_display = ('pk', 'username', 'email', 'is_staff', 'is_active')

admin.site.register(User, UserAdmin)


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    """Admin for company settings."""
    
    list_display = ['company_name', 'company_email', 'company_phone', 'created_at']
    fieldsets = (
        ('Informations de l\'entreprise', {
            'fields': ('company_name', 'company_slogan', 'company_email', 'company_phone', 
                      'company_address', 'company_website', 'tax_id')
        }),
        ('Logo', {
            'fields': ('logo', 'show_logo_on_invoice')
        }),
        ('Couleurs', {
            'fields': ('primary_color', 'secondary_color', 'text_color')
        }),
        ('Personnalisation de la facture', {
            'fields': ('invoice_prefix', 'invoice_header_text', 'invoice_footer_text', 
                      'invoice_footer_note', 'show_tax_breakdown', 'default_payment_terms')
        }),
        ('Informations bancaires', {
            'fields': ('bank_name', 'bank_account', 'mobile_money_number')
        }),
    )
    
    def has_add_permission(self, request):
        """Only allow one settings instance."""
        return not CompanySettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of settings."""
        return False

