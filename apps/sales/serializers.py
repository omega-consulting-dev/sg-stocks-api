"""Sales serializers - Updated 2025-12-15"""
from rest_framework import serializers
from apps.sales.models import Sale, SaleLine, Quote, QuoteLine
from apps.customers.models import Customer


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
    invoice = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'store', 'sale_date', 
            'status', 'status_display', 'total_amount', 'paid_amount', 
            'payment_status', 'payment_status_display', 'lines', 'invoice_id', 'invoice', 'created_at'
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
    
    def get_invoice(self, obj):
        """Return invoice details if invoice exists."""
        if hasattr(obj, 'invoice') and obj.invoice:
            return {
                'id': obj.invoice.id,
                'invoice_number': obj.invoice.invoice_number
            }
        return None


class SaleDetailSerializer(serializers.ModelSerializer):
    """Serializer for sale detail view."""
    
    lines = SaleLineSerializer(many=True, read_only=True)
    customer = serializers.SerializerMethodField()
    store = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    is_fully_paid = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payments = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'store',
            'sale_date', 'status', 'status_display', 'subtotal', 'discount_amount', 'tax_amount',
            'total_amount', 'payment_status', 'paid_amount', 'balance_due',
            'is_fully_paid', 'notes', 'lines', 'payments', 'invoice_id', 'invoice',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_customer(self, obj):
        if obj.customer:
            return {'id': obj.customer.id, 'name': obj.customer.name}
        return None
    
    def get_store(self, obj):
        return {'id': obj.store.id, 'name': obj.store.name}
    
    def get_balance_due(self, obj):
        """Convert Decimal balance_due to float for JSON serialization."""
        return float(obj.balance_due)
    
    def get_is_fully_paid(self, obj):
        """Return is_fully_paid property."""
        return obj.is_fully_paid
    
    def get_payments(self, obj):
        # TODO: Ajouter le modèle Payment plus tard
        # Pour l'instant, retourner une liste vide
        return []
    
    def get_invoice_id(self, obj):
        """Return invoice ID if invoice exists."""
        if hasattr(obj, 'invoice') and obj.invoice:
            return obj.invoice.id
        return None
    
    def get_invoice(self, obj):
        """Return invoice details if invoice exists."""
        if hasattr(obj, 'invoice') and obj.invoice:
            return {
                'id': obj.invoice.id,
                'invoice_number': obj.invoice.invoice_number
            }
        return None


class SaleCreateSerializer(serializers.ModelSerializer):
    """Serializer for sale creation."""
    
    lines = SaleLineSerializer(many=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    payment_method = serializers.ChoiceField(
        choices=[
            ('cash', 'Espèces'),
            ('card', 'Carte'),
            ('transfer', 'Virement'),
            ('mobile_money', 'Mobile Money (MTN/Orange)')
        ],
        required=False,
        default='cash'
    )
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Sale
        fields = [
            'customer', 'store', 'sale_date', 'discount_amount', 'paid_amount', 'payment_method', 'notes', 'lines'
        ]
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        paid_amount = validated_data.pop('paid_amount', 0)
        payment_method = validated_data.pop('payment_method', 'cash')
        customer = validated_data.get('customer')
        
        # Si aucun client n'est fourni, créer ou récupérer un client "Client No Name"
        if not customer:
            from apps.customers.models import Customer
            customer, created = Customer.objects.get_or_create(
                customer_code='CLI00001',
                defaults={
                    'name': 'Client No Name',
                    'phone': '',
                    'email': '',
                    'address': 'N/A',
                    'city': 'N/A',
                    'country': 'Cameroun'
                }
            )
            validated_data['customer'] = customer
        
        # Generate sale number and create sale - thread-safe method
        from django.utils import timezone
        from decimal import Decimal
        from django.db import transaction
        
        # Arrondir paid_amount à 2 décimales pour éviter les problèmes de précision
        if paid_amount:
            paid_amount = Decimal(str(paid_amount)).quantize(Decimal('0.01'))
        
        # Set paid_amount and payment_method in validated_data
        validated_data['paid_amount'] = paid_amount
        validated_data['payment_method'] = payment_method
        
        # Extraire l'année de la sale_date fournie
        sale_date = validated_data.get('sale_date')
        if not sale_date:
            sale_date = timezone.now().date()
            validated_data['sale_date'] = sale_date
        
        sale_year = sale_date.year
        
        # Utiliser une transaction atomique pour TOUT le processus de création
        with transaction.atomic():
            # Récupérer la dernière vente de L'ANNÉE DE LA VENTE en utilisant select_for_update pour éviter les doublons
            last_sale = Sale.objects.filter(
                sale_date__year=sale_year
            ).select_for_update().order_by('-sale_number').first()
            
            if last_sale and last_sale.sale_number:
                # Extraire le numéro séquentiel du dernier numéro (ex: VTE2026000005 → 5)
                try:
                    last_number = int(last_sale.sale_number[-6:])
                    next_number = last_number + 1
                except (ValueError, IndexError):
                    # Si on ne peut pas extraire, compter toutes les ventes de l'année
                    next_number = Sale.objects.filter(sale_date__year=sale_year).count() + 1
            else:
                next_number = 1
            
            validated_data['sale_number'] = f"VTE{sale_year}{next_number:06d}"
            
            # Créer la vente DANS la transaction
            sale = Sale.objects.create(**validated_data)
            
            # Create lines
            for line_data in lines_data:
                SaleLine.objects.create(sale=sale, **line_data)
            
            # Calculate totals (this will also update payment_status based on paid_amount)
            sale.calculate_totals()
            
            # Validation: Les clients de passage (No Name ou sans client) doivent payer la totalité
            is_no_name_customer = False
            if customer:
                # Vérifier si c'est un client "No Name" / "Client de passage"
                customer_name = customer.name.lower() if hasattr(customer, 'name') else ''
                is_no_name_customer = any(keyword in customer_name for keyword in [
                    'no name', 'client no name', 'client de passage', 'passage'
                ])
            
            if (not customer or is_no_name_customer) and sale.balance_due > 0:
                raise serializers.ValidationError({
                    'paid_amount': 'Les clients de passage ne peuvent pas avoir de crédit. Veuillez payer la totalité ou créer un client réel pour autoriser le crédit.'
                })
            
            sale.save()
        
        return sale
    
    def update(self, instance, validated_data):
        """Update sale and its lines."""
        lines_data = validated_data.pop('lines', [])
        paid_amount = validated_data.pop('paid_amount', instance.paid_amount)
        
        # Sauvegarder l'ancien numéro
        old_sale_number = instance.sale_number
        
        # Update sale fields first
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Vérifier si le numéro de vente correspond à l'année de la date
        try:
            year_in_number = int(instance.sale_number[3:7])  # VTEyyyy
            actual_year = instance.sale_date.year
            
            if year_in_number != actual_year:
                # L'année ne correspond pas - régénérer le numéro
                from django.db import transaction
                
                with transaction.atomic():
                    # Get next number for the correct year
                    last_sale = Sale.objects.filter(
                        sale_date__year=actual_year
                    ).exclude(id=instance.id).select_for_update().order_by('-sale_number').first()
                    
                    if last_sale and last_sale.sale_number.startswith(f'VTE{actual_year}'):
                        try:
                            last_number_str = last_sale.sale_number.replace('VTE', '').replace(str(actual_year), '')
                            last_number = int(last_number_str)
                        except (ValueError, AttributeError):
                            last_number = 0
                    else:
                        last_number = 0
                    
                    next_number = last_number + 1
                    instance.sale_number = f"VTE{actual_year}{next_number:06d}"
        except (ValueError, IndexError):
            # Numéro invalide, on le garde
            pass
        
        # Arrondir paid_amount à 2 décimales
        if paid_amount:
            from decimal import Decimal
            paid_amount = Decimal(str(paid_amount)).quantize(Decimal('0.01'))
        
        instance.paid_amount = paid_amount
        
        # Delete existing lines and create new ones
        instance.lines.all().delete()
        
        for line_data in lines_data:
            SaleLine.objects.create(sale=instance, **line_data)
        
        # Recalculate totals
        instance.calculate_totals()
        instance.save()
        
        # Update stock movements references AFTER saving (si le numéro a changé)
        if old_sale_number != instance.sale_number:
            from apps.inventory.models import StockMovement
            updated_count = StockMovement.objects.filter(reference=old_sale_number).update(reference=instance.sale_number)
            print(f"Updated {updated_count} movements: {old_sale_number} → {instance.sale_number}")
        
        # NOTE: Ne pas gérer les mouvements de stock ici !
        # Si la vente est confirmée, le signal auto_generate_invoice_on_confirmation
        # appellera Invoice.update_from_sale() qui gèrera les mouvements de stock
        # via la facture. Cela évite les doublons.
        
        return instance
    
    def partial_update(self, instance, validated_data):
        """Partial update - delegate to full update."""
        return self.update(instance, validated_data)


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
