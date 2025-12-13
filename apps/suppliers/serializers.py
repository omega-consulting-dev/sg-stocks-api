from rest_framework import serializers
from django.db import models
from apps.suppliers.models import Supplier, SupplierPayment, PurchaseOrder


class SupplierListSerializer(serializers.ModelSerializer):
    """Serializer for supplier list view (minimal data)."""
    
    balance = serializers.SerializerMethodField()
    payment_term_display = serializers.CharField(source='get_payment_term_display', read_only=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'supplier_code', 'name', 'contact_person', 'email', 
            'phone', 'city', 'payment_term', 'payment_term_display',
            'rating', 'balance', 'is_active', 'created_at'
        ]
    
    def get_balance(self, obj):
        """Get supplier balance (what we owe)."""
        return float(obj.get_balance())


class SupplierDetailSerializer(serializers.ModelSerializer):
    """Serializer for supplier detail view (complete data)."""
    
    balance = serializers.SerializerMethodField()
    payment_term_display = serializers.CharField(source='get_payment_term_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'supplier_code', 'name', 'contact_person',
            'email', 'phone', 'mobile', 'website',
            'address', 'city', 'postal_code', 'country',
            'tax_id', 'bank_account',
            'payment_term', 'payment_term_display', 'rating',
            'notes', 'balance',
            'user', 'user_email',
            'is_active', 'created_at', 'updated_at',
            'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_balance(self, obj):
        """Get supplier balance (what we owe)."""
        return float(obj.get_balance())


class SupplierCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for supplier creation and update."""
    
    class Meta:
        model = Supplier
        fields = [
            'supplier_code', 'name', 'contact_person',
            'email', 'phone', 'mobile', 'website',
            'address', 'city', 'postal_code', 'country',
            'tax_id', 'bank_account',
            'payment_term', 'rating',
            'notes', 'user', 'is_active'
        ]
    
    def validate_supplier_code(self, value):
        """Ensure supplier code is unique."""
        instance = self.instance
        if instance:
            # Update case - exclude current instance
            if Supplier.objects.exclude(pk=instance.pk).filter(supplier_code=value).exists():
                raise serializers.ValidationError("Ce code fournisseur existe déjà.")
        else:
            # Create case
            if Supplier.objects.filter(supplier_code=value).exists():
                raise serializers.ValidationError("Ce code fournisseur existe déjà.")
        return value
    
    def create(self, validated_data):
        """Auto-generate supplier code if not provided."""
        if not validated_data.get('supplier_code'):
            # Generate supplier code
            count = Supplier.objects.count() + 1
            validated_data['supplier_code'] = f"FRN{count:05d}"
        
        return super().create(validated_data)


class SupplierPaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    purchase_order_number = serializers.CharField(source='purchase_order.order_number', read_only=True, allow_null=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SupplierPayment
        fields = [
            'id', 'payment_number', 'supplier', 'supplier_name', 'purchase_order', 
            'purchase_order_number', 'payment_date', 'amount', 'payment_method', 
            'reference', 'notes', 'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['payment_number', 'created_at', 'created_by', 'created_by_name']
    
    def get_created_by_name(self, obj):
        """Retourne le nom complet de l'utilisateur qui a créé le paiement."""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None
    
    def validate(self, data):
        """Validation du paiement."""
        supplier = data.get('supplier')
        amount = data.get('amount')
        
        if amount and amount <= 0:
            raise serializers.ValidationError({
                'amount': 'Le montant doit être supérieur à 0.'
            })
        
        # Si purchase_order fourni, vérifier qu'il appartient bien au fournisseur
        po = data.get('purchase_order')
        if po and po.supplier != supplier:
            raise serializers.ValidationError({
                'purchase_order': 'Le bon de commande n\'appartient pas à ce fournisseur.'
            })
        
        return data

    def create(self, validated_data):
        """Créer un paiement et répartir automatiquement sur les dettes."""
        from django.utils import timezone
        from decimal import Decimal
        from django.db import transaction

        validated_data['payment_number'] = f"PAY{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        supplier = validated_data.get('supplier')
        amount = Decimal(str(validated_data.get('amount', 0)))
        po = validated_data.get('purchase_order')
        
        with transaction.atomic():
            # Créer le paiement
            payment = SupplierPayment.objects.create(**validated_data)
            
            remaining_amount = amount
            
            if po:
                # Si un PurchaseOrder spécifique est fourni, appliquer le paiement dessus
                # Note: paid_amount sera mis à jour automatiquement par le signal
                
                balance = po.total_amount - (po.paid_amount or Decimal('0'))
                amount_to_apply = min(remaining_amount, balance)
                
                remaining_amount -= amount_to_apply
                
                # Si il reste de l'argent, le répartir sur les autres dettes
                if remaining_amount > 0:
                    other_pos = PurchaseOrder.objects.filter(
                        supplier=supplier,
                        status__in=['confirmed', 'received']
                    ).exclude(id=po.id).annotate(
                        balance=models.F('total_amount') - models.F('paid_amount')
                    ).filter(balance__gt=0).order_by('order_date')
                    
                    for other_po in other_pos:
                        if remaining_amount <= 0:
                            break
                        
                        balance = other_po.total_amount - (other_po.paid_amount or Decimal('0'))
                        amount_to_apply = min(remaining_amount, balance)
                        
                        # Créer un paiement additionnel pour ce PO
                        # Note: paid_amount sera mis à jour automatiquement par le signal
                        additional_payment = SupplierPayment.objects.create(
                            payment_number=f"PAY{timezone.now().strftime('%Y%m%d%H%M%S%f')}",
                            supplier=supplier,
                            purchase_order=other_po,
                            payment_date=validated_data['payment_date'],
                            amount=amount_to_apply,
                            payment_method=validated_data['payment_method'],
                            reference=f"{validated_data.get('reference', '')} (répartition auto)",
                            notes=f"Paiement réparti automatiquement depuis {payment.payment_number}"
                        )
                        
                        remaining_amount -= amount_to_apply
            else:
                # Aucun PurchaseOrder spécifié : répartir automatiquement sur toutes les dettes
                # Récupérer tous les PurchaseOrders avec dette du fournisseur
                pos_with_debt = PurchaseOrder.objects.filter(
                    supplier=supplier,
                    status__in=['confirmed', 'received']
                ).annotate(
                    balance=models.F('total_amount') - models.F('paid_amount')
                ).filter(balance__gt=0).order_by('due_date', 'order_date')
                
                if not pos_with_debt.exists():
                    raise serializers.ValidationError({
                        'supplier': 'Ce fournisseur n\'a aucune dette à payer. Le paiement ne peut pas être enregistré.'
                    })
                
                # Attacher le paiement au premier PurchaseOrder
                first_po = pos_with_debt.first()
                payment.purchase_order = first_po
                payment.save()
                
                # Répartir le montant sur les dettes par ordre de date d'échéance
                for po_debt in pos_with_debt:
                    if remaining_amount <= 0:
                        break
                    
                    balance = po_debt.total_amount - (po_debt.paid_amount or Decimal('0'))
                    amount_to_apply = min(remaining_amount, balance)
                    
                    if po_debt.id != first_po.id:
                        # Autres POs : créer des paiements additionnels
                        # Note: paid_amount sera mis à jour automatiquement par le signal
                        additional_payment = SupplierPayment.objects.create(
                            payment_number=f"PAY{timezone.now().strftime('%Y%m%d%H%M%S%f')}",
                            supplier=supplier,
                            purchase_order=po_debt,
                            payment_date=validated_data['payment_date'],
                            amount=amount_to_apply,
                            payment_method=validated_data['payment_method'],
                            reference=f"{validated_data.get('reference', '')} (répartition auto)",
                            notes=f"Paiement réparti automatiquement depuis {payment.payment_number}"
                        )
                    
                    remaining_amount -= amount_to_apply
            
            # Si il reste encore de l'argent (surprenant mais possible), logger une note
            if remaining_amount > 0:
                payment.notes = (payment.notes or '') + f"\n[ALERTE] Montant excédentaire: {remaining_amount} FCFA non affecté."
                payment.save()
        
        return payment
