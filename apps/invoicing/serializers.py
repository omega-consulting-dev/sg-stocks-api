from rest_framework import serializers
from apps.invoicing.models import Invoice, InvoiceLine, InvoicePayment
from django.utils import timezone
from datetime import timedelta


class InvoiceLineSerializer(serializers.ModelSerializer):
    """Serializer for InvoiceLine model."""
    
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True, allow_null=True)
    service_name = serializers.CharField(source='service.name', read_only=True, allow_null=True)
    
    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'product', 'product_name', 'service', 'service_name', 'description', 
            'quantity', 'unit_price', 'tax_rate', 'discount_percentage', 
            'subtotal', 'tax_amount', 'total'
        ]


class InvoicePaymentSerializer(serializers.ModelSerializer):
    """Serializer for InvoicePayment model."""
    
    payment_number = serializers.CharField(required=False, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = InvoicePayment
        fields = [
            'id', 'payment_number', 'invoice', 'payment_date', 'amount',
            'payment_method', 'status', 'status_display', 'reference', 'notes', 'created_at'
        ]
        read_only_fields = ['payment_number', 'status_display', 'created_at']


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer for invoice list view."""
    
    lines = InvoiceLineSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    total_items = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'customer', 'customer_name', 'store', 'store_name',
            'invoice_date', 'due_date', 'status', 'status_display',
            'total_amount', 'paid_amount', 'balance_due', 'is_overdue',
            'total_items', 'lines', 'created_at'
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Serializer for invoice detail view."""
    
    lines = InvoiceLineSerializer(many=True, read_only=True)
    payments = InvoicePaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_fully_paid = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'customer', 'customer_name', 'store', 'store_name', 'sale',
            'invoice_date', 'due_date', 'status', 'payment_term',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'paid_amount', 'balance_due', 'is_fully_paid', 'is_overdue',
            'notes', 'lines', 'payments',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def update(self, instance, validated_data):
        """Update invoice - regenerate invoice_number if year doesn't match."""
        # Sauvegarder l'ancien numéro pour mettre à jour les mouvements
        old_invoice_number = instance.invoice_number
        
        # Update invoice fields first
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Vérifier si le numéro de facture correspond à l'année de la date
        # Extraire l'année du numéro actuel (FACyyyy...)
        try:
            year_in_number = int(instance.invoice_number[3:7])
            actual_year = instance.invoice_date.year
            
            if year_in_number != actual_year:
                # L'année ne correspond pas - régénérer le numéro
                from django.db import transaction
                
                with transaction.atomic():
                    # Get next number for the correct year
                    last_invoice = Invoice.objects.filter(
                        invoice_date__year=actual_year
                    ).exclude(id=instance.id).select_for_update().order_by('-invoice_number').first()
                    
                    if last_invoice and last_invoice.invoice_number.startswith(f'FAC{actual_year}'):
                        try:
                            last_number_str = last_invoice.invoice_number.replace('FAC', '').replace(str(actual_year), '')
                            last_number = int(last_number_str)
                        except (ValueError, AttributeError):
                            last_number = 0
                    else:
                        last_number = 0
                    
                    next_number = last_number + 1
                    instance.invoice_number = f"FAC{actual_year}{next_number:06d}"
        except (ValueError, IndexError):
            # Numéro de facture invalide, on le garde tel quel
            pass
        
        # Recalculate due date if payment_term or invoice_date changed
        if 'payment_term' in validated_data or 'invoice_date' in validated_data:
            payment_term = instance.payment_term
            days_map = {
                'immediate': 0,
                '15_days': 15,
                '30_days': 30,
                '60_days': 60,
            }
            days = days_map.get(payment_term, 30)
            instance.due_date = instance.invoice_date + timedelta(days=days)
        
        instance.save()
        
        # Update stock movements references AFTER saving (si le numéro a changé)
        if old_invoice_number != instance.invoice_number:
            from apps.inventory.models import StockMovement
            old_ref = f"FACT-{old_invoice_number}"
            new_ref = f"FACT-{instance.invoice_number}"
            updated_count = StockMovement.objects.filter(reference=old_ref).update(reference=new_ref)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Updated {updated_count} movements: {old_ref} → {new_ref}")
        
        return instance


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for invoice creation."""
    
    lines = InvoiceLineSerializer(many=True)
    
    class Meta:
        model = Invoice
        fields = [
            'customer', 'store', 'sale', 'invoice_date', 'payment_term',
            'discount_amount', 'notes', 'lines'
        ]
    
    def create(self, validated_data):
        from django.db import transaction
        
        lines_data = validated_data.pop('lines')
        
        # Utiliser une transaction atomique pour tout annuler si le stock est insuffisant
        with transaction.atomic():
            # Generate invoice number using invoice_date year (not current year)
            invoice_date = validated_data.get('invoice_date', timezone.now().date())
            year = invoice_date.year
            count = Invoice.objects.filter(invoice_date__year=year).count() + 1
            validated_data['invoice_number'] = f"FAC{year}{count:06d}"
            
            # Calculate due date based on payment term
            payment_term = validated_data.get('payment_term', '30_days')
            days_map = {
                'immediate': 0,
                '15_days': 15,
                '30_days': 30,
                '60_days': 60,
            }
            days = days_map.get(payment_term, 30)
            validated_data['due_date'] = validated_data['invoice_date'] + timedelta(days=days)
            
            invoice = Invoice.objects.create(**validated_data)
            
            # Create lines
            for line_data in lines_data:
                InvoiceLine.objects.create(invoice=invoice, **line_data)
            
            # Calculate totals
            invoice.subtotal = sum(line.subtotal_after_discount for line in invoice.lines.all())
            invoice.tax_amount = sum(line.tax_amount for line in invoice.lines.all())
            invoice.total_amount = invoice.subtotal + invoice.tax_amount
            invoice.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])
            
            # Créer les mouvements de stock maintenant que les lignes existent
            # Si le stock est insuffisant, une ValidationError sera levée et la transaction sera annulée
            from apps.invoicing.models import create_stock_movements_from_invoice
            create_stock_movements_from_invoice(sender=Invoice, instance=invoice, created=True)
            
            return invoice
    
    def update(self, instance, validated_data):
        """Update invoice - regenerate invoice_number if year doesn't match."""
        lines_data = validated_data.pop('lines', None)
        
        # Sauvegarder l'ancien numéro pour mettre à jour les mouvements
        old_invoice_number = instance.invoice_number
        
        # Update invoice fields first
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Vérifier si le numéro de facture correspond à l'année de la date
        # Extraire l'année du numéro actuel (FACyyyy...)
        try:
            year_in_number = int(instance.invoice_number[3:7])
            actual_year = instance.invoice_date.year
            
            if year_in_number != actual_year:
                # L'année ne correspond pas - régénérer le numéro
                from django.db import transaction
                
                with transaction.atomic():
                    # Get next number for the correct year
                    last_invoice = Invoice.objects.filter(
                        invoice_date__year=actual_year
                    ).exclude(id=instance.id).select_for_update().order_by('-invoice_number').first()
                    
                    if last_invoice and last_invoice.invoice_number.startswith(f'FAC{actual_year}'):
                        try:
                            last_number_str = last_invoice.invoice_number.replace('FAC', '').replace(str(actual_year), '')
                            last_number = int(last_number_str)
                        except (ValueError, AttributeError):
                            last_number = 0
                    else:
                        last_number = 0
                    
                    next_number = last_number + 1
                    instance.invoice_number = f"FAC{actual_year}{next_number:06d}"
        except (ValueError, IndexError):
            # Numéro de facture invalide, on le garde tel quel
            pass
        
        # Recalculate due date if payment_term or invoice_date changed
        if 'payment_term' in validated_data or 'invoice_date' in validated_data:
            payment_term = instance.payment_term
            days_map = {
                'immediate': 0,
                '15_days': 15,
                '30_days': 30,
                '60_days': 60,
            }
            days = days_map.get(payment_term, 30)
            instance.due_date = instance.invoice_date + timedelta(days=days)
        
        instance.save()
        
        # Update stock movements references AFTER saving (si le numéro a changé)
        if old_invoice_number != instance.invoice_number:
            from apps.inventory.models import StockMovement
            old_ref = f"FACT-{old_invoice_number}"
            new_ref = f"FACT-{instance.invoice_number}"
            updated_count = StockMovement.objects.filter(reference=old_ref).update(reference=new_ref)
            print(f"Updated {updated_count} movements: {old_ref} → {new_ref}")
        
        # Update lines if provided
        if lines_data is not None:
            # Delete existing lines
            instance.lines.all().delete()
            
            for line_data in lines_data:
                InvoiceLine.objects.create(invoice=instance, **line_data)
            
            # Recalculate totals
            instance.subtotal = sum(line.subtotal_after_discount for line in instance.lines.all())
            instance.tax_amount = sum(line.tax_amount for line in instance.lines.all())
            instance.total_amount = instance.subtotal + instance.tax_amount
            instance.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])
        
        return instance