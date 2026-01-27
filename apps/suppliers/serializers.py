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
            last_supplier = Supplier.objects.order_by('-id').first()
            if last_supplier and last_supplier.supplier_code:
                try:
                    last_number = int(last_supplier.supplier_code.replace('FRN', ''))
                    next_number = last_number + 1
                except (ValueError, AttributeError):
                    next_number = Supplier.objects.count() + 1
            else:
                next_number = 1
            
            supplier_code = f"FRN{next_number:05d}"
            while Supplier.objects.filter(supplier_code=supplier_code).exists():
                next_number += 1
                supplier_code = f"FRN{next_number:05d}"
            
            validated_data['supplier_code'] = supplier_code
        
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
        from apps.cashbox.models import Cashbox, CashboxSession, CashMovement
        from django.db.models import Sum

        validated_data['payment_number'] = f"PAY{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        supplier = validated_data.get('supplier')
        amount = Decimal(str(validated_data.get('amount', 0)))
        po = validated_data.get('purchase_order')
        payment_method = validated_data.get('payment_method')
        request = self.context['request']
        
        # Vérifier et créer le mouvement de caisse/banque si nécessaire
        if payment_method in ['cash', 'bank_transfer']:
            # Récupérer le store depuis la requête (ou utiliser le premier store disponible)
            store_id = request.data.get('store_id')
            store = None
            
            if store_id:
                from apps.inventory.models import Store
                try:
                    store = Store.objects.get(id=store_id)
                except Store.DoesNotExist:
                    pass
            
            # Si pas de store spécifié, utiliser le premier store disponible
            if not store:
                from apps.inventory.models import Store
                store = Store.objects.first()
            
            if store:
                # Récupérer ou créer la caisse
                cashbox, _ = Cashbox.objects.get_or_create(
                    store=store,
                    is_active=True,
                    defaults={
                        'name': f'Caisse {store.name}',
                        'code': f'CASH-{store.code}',
                        'created_by': request.user
                    }
                )
                
                # Récupérer ou créer une session ouverte
                cashbox_session, _ = CashboxSession.objects.get_or_create(
                    cashbox=cashbox,
                    status='open',
                    defaults={
                        'cashier': request.user,
                        'opening_date': timezone.now(),
                        'opening_balance': 0,
                        'created_by': request.user
                    }
                )
                
                # Vérifier le solde disponible avant de créer le mouvement
                if payment_method == 'cash':
                    current_balance = cashbox.current_balance
                    if amount > current_balance:
                        raise serializers.ValidationError({
                            'amount': f'Solde insuffisant. Solde disponible: {current_balance} FCFA'
                        })
                
                elif payment_method == 'bank_transfer':
                    # Calculer le solde bancaire disponible
                    bank_deposits = CashMovement.objects.filter(
                        category='bank_deposit',
                        movement_type='out'
                    ).aggregate(total=Sum('amount'))['total'] or 0
                    
                    bank_withdrawals = CashMovement.objects.filter(
                        category='bank_withdrawal',
                        movement_type='in'
                    ).aggregate(total=Sum('amount'))['total'] or 0
                    
                    bank_balance = bank_deposits - bank_withdrawals
                    
                    if amount > bank_balance:
                        raise serializers.ValidationError({
                            'amount': f'Solde bancaire insuffisant. Solde disponible: {bank_balance} FCFA'
                        })
        
        with transaction.atomic():
            # Créer le paiement
            payment = SupplierPayment.objects.create(**validated_data)
            
            # Créer le mouvement de caisse/banque correspondant
            if payment_method in ['cash', 'bank_transfer'] and store:
                last_movement = CashMovement.objects.order_by('-id').first()
                if last_movement and last_movement.movement_number:
                    try:
                        # Extraire le numéro du dernier mouvement
                        import re
                        match = re.search(r'\d+', last_movement.movement_number)
                        if match:
                            last_number = int(match.group())
                            movement_count = last_number + 1
                        else:
                            movement_count = CashMovement.objects.count() + 1
                    except (ValueError, AttributeError):
                        movement_count = CashMovement.objects.count() + 1
                else:
                    movement_count = 1
                
                if payment_method == 'cash':
                    # Paiement en espèces: argent sort de la caisse
                    CashMovement.objects.create(
                        movement_number=f'SUPP-{movement_count:05d}',
                        cashbox_session=cashbox_session,
                        movement_type='out',
                        category='supplier_payment',
                        amount=amount,
                        payment_method='cash',
                        reference=payment.payment_number,
                        description=f'Règlement fournisseur {supplier.name} en espèces',
                        created_by=request.user
                    )
                    
                    # Mettre à jour le solde de la caisse
                    cashbox.current_balance -= amount
                    cashbox.save()
                    
                # Note: Pour les paiements par virement bancaire, on ne crée PAS de CashMovement
                # car l'argent ne passe pas par la caisse physique.
                # Le SupplierPayment avec payment_method='bank_transfer' est suffisant
                # et sera pris en compte dans le calcul du solde bancaire via get_bank_balance()
                    
                    # Mettre à jour le solde de la caisse
                    cashbox.current_balance += amount
                    cashbox.save()
            
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
