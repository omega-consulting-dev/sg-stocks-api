from rest_framework import serializers
from apps.main.models_settings import CompanySettings


class CompanySettingsSerializer(serializers.ModelSerializer):
    """Serializer for company settings."""
    
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CompanySettings
        fields = [
            'id',
            'company_name',
            'company_slogan',
            'company_email',
            'company_phone',
            'company_address',
            'company_website',
            'tax_id',
            'logo',
            'logo_url',
            'primary_color',
            'secondary_color',
            'text_color',
            'invoice_header_text',
            'show_logo_on_invoice',
            'invoice_footer_text',
            'invoice_footer_note',
            'bank_name',
            'bank_account',
            'mobile_money_number',
            'invoice_prefix',
            'show_tax_breakdown',
            'default_payment_terms',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_logo_url(self, obj):
        """Get full URL for logo."""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None
