from rest_framework import serializers
from apps.cashbox.models import Cashbox, CashboxSession, CashMovement, CashCount


class CashboxSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = Cashbox
        fields = ['id', 'name', 'code', 'store', 'store_name', 'current_balance', 'is_active', 'created_at']


class CashboxSessionSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source='cashier.get_full_name', read_only=True)
    difference = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = CashboxSession
        fields = [
            'id', 'cashbox', 'cashier', 'cashier_name', 'opening_date', 'closing_date',
            'status', 'opening_balance', 'expected_closing_balance', 'actual_closing_balance',
            'difference', 'opening_notes', 'closing_notes', 'created_at'
        ]


class CashMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashMovement
        fields = [
            'id', 'movement_number', 'cashbox_session', 'movement_type', 'category',
            'amount', 'payment_method', 'reference', 'sale', 'description', 'notes', 'created_at'
        ]
