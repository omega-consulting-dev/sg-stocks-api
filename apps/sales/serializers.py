"""Sales serializers - Updated 2025-12-15"""
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
        if obj.product:
            return obj.product.name
        elif obj.service:
            return obj.service.name
        return obj.description or 'N/A'


class SaleListSerializer(serializers.ModelSerializer):
    """Serializer for sale list view."""
    
    customer = serializers.SerializerMethodField()
    store = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    lines = SaleLineSerializer(many=True, read_only=True)
    invoice_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'store', 'sale_date', 
            'status', 'status_display', 'total_amount', 'paid_amount', 
            'payment_status', 'payment_status_display', 'lines', 'invoice_id', 'created_at'
        ]
    
    def get_customer(self, obj):
        if obj.customer:
            return {'id': obj.customer.id, 'name': obj.customer.name}
        return None
    
    def get_store(self, obj):
        return {'id': obj.store.id, 'name': obj.store.name}
    
    def get_invoice_id(self, obj):
        """Return invoice ID if invoice exists."""
        if hasattr(obj, 'invoice') and obj.invoice:
            return obj.invoice.id
        return None


class SaleDetailSerializer(serializers.ModelSerializer):
    """Serializer for sale detail view."""
    
    lines = SaleLineSerializer(many=True, read_only=True)
    customer = serializers.SerializerMethodField()
    store = serializers.SerializerMethodField()
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_fully_paid = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payments = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'store',
            'sale_date', 'status', 'status_display', 'subtotal', 'discount_amount', 'tax_amount',
            'total_amount', 'payment_status', 'paid_amount', 'balance_due',
            'is_fully_paid', 'notes', 'lines', 'payments', 'invoice_id',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_customer(self, obj):
        if obj.customer:
            return {'id': obj.customer.id, 'name': obj.customer.name}
        return None
    
    def get_store(self, obj):
        return {'id': obj.store.id, 'name': obj.store.name}
    
    def get_payments(self, obj):
        # TODO: Ajouter le modèle Payment plus tard
        # Pour l'instant, retourner une liste vide
        return []
    
    def get_invoice_id(self, obj):
        """Return invoice ID if invoice exists."""
        if hasattr(obj, 'invoice') and obj.invoice:
            return obj.invoice.id
        return None


class SaleCreateSerializer(serializers.ModelSerializer):
    """Serializer for sale creation."""
    
    lines = SaleLineSerializer(many=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    
    class Meta:
        model = Sale
        fields = [
            'customer', 'store', 'sale_date', 'discount_amount', 'paid_amount', 'notes', 'lines'
        ]
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        paid_amount = validated_data.pop('paid_amount', 0)
        
        # Generate sale number
        from django.utils import timezone
        from decimal import Decimal
        count = Sale.objects.filter(sale_date__year=timezone.now().year).count() + 1
        validated_data['sale_number'] = f"VTE{timezone.now().year}{count:06d}"
        
        # Arrondir paid_amount à 2 décimales pour éviter les problèmes de précision
        if paid_amount:
            paid_amount = Decimal(str(paid_amount)).quantize(Decimal('0.01'))
        
        # Set paid_amount in validated_data
        validated_data['paid_amount'] = paid_amount
        
        sale = Sale.objects.create(**validated_data)
        
        # Create lines
        for line_data in lines_data:
            SaleLine.objects.create(sale=sale, **line_data)
        
        # Calculate totals (this will also update payment_status based on paid_amount)
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
