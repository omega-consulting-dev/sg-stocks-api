from rest_framework import serializers
from apps.sales.models import Sale, SaleLine, Quote, QuoteLine


class SaleLineSerializer(serializers.ModelSerializer):
    """Serializer for SaleLine model."""
    
    item_name = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = SaleLine
        fields = [
            'id', 'line_type', 'product', 'service', 'item_name',
            'description', 'quantity', 'unit_price', 'tax_rate',
            'discount_percentage', 'subtotal', 'tax_amount', 'total'
        ]
    
    def get_item_name(self, obj):
        return obj.product.name if obj.product else obj.service.name


class SaleListSerializer(serializers.ModelSerializer):
    """Serializer for sale list view."""
    
    customer_name = serializers.CharField(source='customer.get_display_name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'customer_name',
            'store', 'store_name', 'sale_date', 'status', 'status_display',
            'total_amount', 'paid_amount', 'payment_status', 'payment_status_display',
            'created_at'
        ]


class SaleDetailSerializer(serializers.ModelSerializer):
    """Serializer for sale detail view."""
    
    lines = SaleLineSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.get_display_name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_fully_paid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'customer_name', 'store', 'store_name',
            'sale_date', 'status', 'subtotal', 'discount_amount', 'tax_amount',
            'total_amount', 'payment_status', 'paid_amount', 'balance_due',
            'is_fully_paid', 'notes', 'lines',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class SaleCreateSerializer(serializers.ModelSerializer):
    """Serializer for sale creation."""
    
    lines = SaleLineSerializer(many=True)
    
    class Meta:
        model = Sale
        fields = [
            'customer', 'store', 'sale_date', 'discount_amount', 'notes', 'lines'
        ]
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        
        # Generate sale number
        from django.utils import timezone
        count = Sale.objects.filter(sale_date__year=timezone.now().year).count() + 1
        validated_data['sale_number'] = f"VTE{timezone.now().year}{count:06d}"
        
        sale = Sale.objects.create(**validated_data)
        
        # Create lines
        for line_data in lines_data:
            SaleLine.objects.create(sale=sale, **line_data)
        
        # Calculate totals
        sale.calculate_totals()
        sale.save()
        
        return sale


class QuoteLineSerializer(serializers.ModelSerializer):
    """Serializer for QuoteLine model."""
    
    item_name = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = QuoteLine
        fields = [
            'id', 'line_type', 'product', 'service', 'item_name',
            'description', 'quantity', 'unit_price', 'tax_rate',
            'discount_percentage', 'subtotal', 'total'
        ]
    
    def get_item_name(self, obj):
        return obj.product.name if obj.product else obj.service.name


class QuoteSerializer(serializers.ModelSerializer):
    """Serializer for Quote model."""
    
    lines = QuoteLineSerializer(many=True)
    customer_name = serializers.CharField(source='customer.get_display_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Quote
        fields = [
            'id', 'quote_number', 'customer', 'customer_name', 'store',
            'quote_date', 'valid_until', 'status', 'status_display',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'notes', 'terms_and_conditions', 'lines',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']