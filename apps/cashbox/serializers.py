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
    description = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    movement_number = serializers.CharField(read_only=True)
    
    class Meta:
        model = CashMovement
        fields = [
            'id', 'movement_number', 'cashbox_session', 'movement_type', 'category',
            'amount', 'payment_method', 'reference', 'sale', 'description', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'movement_number', 'created_at']


class EncaissementSerializer(serializers.Serializer):
    """Serializer pour agréger tous les encaissements (paiements de factures, ventes, etc.)"""
    id = serializers.IntegerField()
    code = serializers.CharField(max_length=50)
    type = serializers.CharField(max_length=50)  # 'invoice_payment' ou 'sale'
    date = serializers.DateField()
    reference_facture = serializers.CharField(max_length=100, allow_blank=True)
    montant = serializers.DecimalField(max_digits=12, decimal_places=2)
    mode_paiement = serializers.CharField(max_length=50)
    client = serializers.CharField(max_length=200, allow_blank=True)
    created_at = serializers.DateTimeField()

