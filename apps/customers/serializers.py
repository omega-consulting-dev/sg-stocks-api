"""
Customer serializers for API.
"""

from rest_framework import serializers
from apps.customers.models import Customer, CustomerContact


class CustomerContactSerializer(serializers.ModelSerializer):
    """Serializer for customer contacts."""
    
    class Meta:
        model = CustomerContact
        fields = [
            'id', 'name', 'position', 'email', 'phone', 'mobile',
            'is_primary', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CustomerListSerializer(serializers.ModelSerializer):
    """Serializer for customer list view (minimal data)."""
    
    balance = serializers.SerializerMethodField()
    payment_term_display = serializers.CharField(source='get_payment_term_display', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_code', 'name', 'email', 'phone', 'city',
            'payment_term', 'payment_term_display', 'credit_limit',
            'balance', 'is_active', 'created_at'
        ]
    
    def get_balance(self, obj):
        """Get customer balance."""
        return float(obj.get_balance())


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Serializer for customer detail view (complete data)."""
    
    balance = serializers.SerializerMethodField()
    payment_term_display = serializers.CharField(source='get_payment_term_display', read_only=True)
    contacts = CustomerContactSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_code', 'name', 'email', 'phone', 'mobile',
            'address', 'city', 'postal_code', 'country',
            'billing_address', 'tax_id',
            'payment_term', 'payment_term_display', 'credit_limit',
            'notes', 'balance', 'contacts',
            'user', 'user_email',
            'is_active', 'created_at', 'updated_at',
            'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_balance(self, obj):
        """Get customer balance."""
        return float(obj.get_balance())


class CustomerCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for customer creation and update."""
    
    customer_code = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_code', 'name', 'email', 'phone', 'mobile',
            'address', 'city', 'postal_code', 'country',
            'billing_address', 'tax_id',
            'payment_term', 'credit_limit',
            'notes', 'user', 'is_active'
        ]
        read_only_fields = ['id']
    
    def validate_customer_code(self, value):
        """Ensure customer code is unique among active customers."""
        instance = self.instance
        queryset = Customer.objects.filter(customer_code=value, is_active=True)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ce code client existe déjà.")
        return value
    
    def create(self, validated_data):
        """Auto-generate customer code if not provided."""
        if not validated_data.get('customer_code'):
            # Generate unique customer code using GLOBAL count (not filtered by user)
            # This ensures caissiers don't generate duplicate codes
            from django.db import connection
            
            # Use raw query to bypass any tenant/user filtering
            with connection.cursor() as cursor:
                cursor.execute("SELECT MAX(id) FROM customers_customer")
                result = cursor.fetchone()
                next_id = (result[0] + 1) if result[0] else 1
            
            validated_data['customer_code'] = f"CLI{next_id:05d}"
            
            # Ensure uniqueness among active customers in case of concurrent requests
            while Customer.objects.filter(customer_code=validated_data['customer_code'], is_active=True).exists():
                next_id += 1
                validated_data['customer_code'] = f"CLI{next_id:05d}"
        
        return super().create(validated_data)
