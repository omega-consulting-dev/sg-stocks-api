from rest_framework import serializers
from apps.suppliers.models import SupplierPayment, PurchaseOrder


class SupplierPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = [
            'id', 'payment_number', 'supplier', 'purchase_order', 'payment_date',
            'amount', 'payment_method', 'reference', 'notes', 'created_at', 'created_by'
        ]
        read_only_fields = ['payment_number', 'created_at', 'created_by']

    def create(self, validated_data):
        # Generate payment number
        from django.utils import timezone
        from decimal import Decimal

        validated_data['payment_number'] = f"PAY{timezone.now().strftime('%Y%m%d%H%M%S')}"
        payment = SupplierPayment.objects.create(**validated_data)

        # Update purchase order paid_amount if provided
        po = validated_data.get('purchase_order')
        if po:
            po.paid_amount = (po.paid_amount or Decimal('0')) + Decimal(str(validated_data.get('amount', 0)))
            po.save()

        return payment
