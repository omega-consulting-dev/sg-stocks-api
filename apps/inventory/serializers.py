"""
Inventory serializers for API.
"""

from rest_framework import serializers
from apps.inventory.models import (
    Store, Stock, StockMovement, StockTransfer, StockTransferLine,
    Inventory, InventoryLine
)


class StoreMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for Store (for references)."""
    
    class Meta:
        model = Store
        fields = ['id', 'code', 'name', 'store_type']


class StoreSerializer(serializers.ModelSerializer):
    """Serializer for Store model."""
    
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    store_type_display = serializers.CharField(source='get_store_type_display', read_only=True)
    stock_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'code', 'name', 'address', 'city', 'phone', 'email',
            'manager', 'manager_name', 'store_type', 'store_type_display',
            'stock_value', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_stock_value(self, obj):
        """Calculate total stock value."""
        from django.db.models import Sum, F
        total = obj.stocks.aggregate(
            total=Sum(F('quantity') * F('product__cost_price'))
        )['total']
        return float(total or 0)


class StockSerializer(serializers.ModelSerializer):
    """Serializer for Stock model."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_reference = serializers.CharField(source='product.reference', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Stock
        fields = [
            'id', 'product', 'product_name', 'product_reference',
            'store', 'store_name', 'quantity', 'reserved_quantity',
            'available_quantity', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StockMovementSerializer(serializers.ModelSerializer):
    """Serializer for StockMovement model."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    destination_store_name = serializers.CharField(
        source='destination_store.name',
        read_only=True
    )
    movement_type_display = serializers.CharField(
        source='get_movement_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'store', 'store_name',
            'movement_type', 'movement_type_display', 'quantity',
            'reference', 'destination_store', 'destination_store_name',
            'notes', 'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'created_by', 'created_by_name']


class StockTransferLineSerializer(serializers.ModelSerializer):
    """Serializer for StockTransferLine model."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = StockTransferLine
        fields = [
            'id', 'product', 'product_name', 'quantity_requested',
            'quantity_sent', 'quantity_received', 'notes'
        ]


class StockTransferListSerializer(serializers.ModelSerializer):
    """Serializer for StockTransfer list view."""
    
    source_store_name = serializers.CharField(source='source_store.name', read_only=True)
    destination_store_name = serializers.CharField(source='destination_store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    lines_count = serializers.IntegerField(source='lines.count', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = [
            'id', 'transfer_number', 'source_store', 'source_store_name',
            'destination_store', 'destination_store_name', 'status',
            'status_display', 'transfer_date', 'lines_count', 'created_at'
        ]


class StockTransferDetailSerializer(serializers.ModelSerializer):
    """Serializer for StockTransfer detail view."""
    
    source_store_detail = StoreMinimalSerializer(source='source_store', read_only=True)
    destination_store_detail = StoreMinimalSerializer(source='destination_store', read_only=True)
    lines = StockTransferLineSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = [
            'id', 'transfer_number', 'source_store', 'source_store_detail',
            'destination_store', 'destination_store_detail', 'status',
            'status_display', 'transfer_date', 'expected_arrival',
            'actual_arrival', 'validated_by', 'received_by', 'notes',
            'lines', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StockTransferCreateSerializer(serializers.ModelSerializer):
    """Serializer for StockTransfer creation."""
    
    lines = StockTransferLineSerializer(many=True)
    
    class Meta:
        model = StockTransfer
        fields = [
            'source_store', 'destination_store', 'transfer_date',
            'expected_arrival', 'notes', 'lines'
        ]
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        
        # Generate transfer number
        from django.utils import timezone
        count = StockTransfer.objects.filter(
            created_at__year=timezone.now().year
        ).count() + 1
        validated_data['transfer_number'] = f"TR{timezone.now().year}{count:05d}"
        
        transfer = StockTransfer.objects.create(**validated_data)
        
        # Create lines
        for line_data in lines_data:
            StockTransferLine.objects.create(transfer=transfer, **line_data)
        
        return transfer


class InventoryLineSerializer(serializers.ModelSerializer):
    """Serializer for InventoryLine model."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    difference = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = InventoryLine
        fields = [
            'id', 'product', 'product_name', 'theoretical_quantity',
            'counted_quantity', 'difference', 'notes'
        ]


class InventoryListSerializer(serializers.ModelSerializer):
    """Serializer for Inventory list view."""
    
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    lines_count = serializers.IntegerField(source='lines.count', read_only=True)
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'inventory_number', 'store', 'store_name',
            'inventory_date', 'status', 'status_display',
            'lines_count', 'created_at'
        ]


class InventoryDetailSerializer(serializers.ModelSerializer):
    """Serializer for Inventory detail view."""
    
    store_detail = StoreMinimalSerializer(source='store', read_only=True)
    lines = InventoryLineSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'inventory_number', 'store', 'store_detail',
            'inventory_date', 'status', 'status_display',
            'validated_by', 'validation_date', 'notes',
            'lines', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class InventoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for Inventory creation."""
    
    lines = InventoryLineSerializer(many=True)
    
    class Meta:
        model = Inventory
        fields = ['store', 'inventory_date', 'notes', 'lines']
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        
        # Generate inventory number
        from django.utils import timezone
        count = Inventory.objects.filter(
            inventory_date__year=timezone.now().year
        ).count() + 1
        validated_data['inventory_number'] = f"INV{timezone.now().year}{count:05d}"
        
        inventory = Inventory.objects.create(**validated_data)
        
        # Create lines
        for line_data in lines_data:
            InventoryLine.objects.create(inventory=inventory, **line_data)
        
        return inventory