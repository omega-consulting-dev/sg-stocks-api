"""
Inventory serializers for API.
"""

from rest_framework import serializers
from apps.inventory.models import (
    Store, Stock, StockMovement, StockTransfer, StockTransferLine,
    Inventory, InventoryLine
)
from apps.suppliers.models import Supplier, PurchaseOrder, PurchaseOrderLine, SupplierPayment
from django.utils import timezone
from django.db import transaction
from decimal import Decimal


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
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
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
    
    def get_customer_name(self, obj):
        """Retrieve customer name from related Invoice for 'out' movements."""
        if obj.invoice and obj.invoice.customer:
            return obj.invoice.customer.name
        return None
    
    # Read-only payment info fields (retrieved from related PurchaseOrder and SupplierPayment)
    payment_info = serializers.SerializerMethodField(read_only=True)
    
    # Optional: allow passing a purchase_order_number to link/create a PO
    purchase_order_number = serializers.CharField(write_only=True, required=False, allow_null=True)
    # Debt / payment handling
    invoice_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Montant total de la facture"
    )
    is_debt = serializers.BooleanField(write_only=True, required=False, default=False)
    due_date = serializers.DateField(write_only=True, required=False, allow_null=True)
    payment_amount = serializers.DecimalField(
        write_only=True,
        required=False,
        max_digits=12,
        decimal_places=2,
        help_text="Montant versé au fournisseur (obligatoire pour les entrées en stock)"
    )
    payment_date = serializers.DateField(write_only=True, required=False, allow_null=True)
    payment_method = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    
    def get_payment_info(self, obj):
        """Retrieve payment information from related PurchaseOrder."""
        # Utiliser invoice_amount du modèle (saisi par l'utilisateur)
        invoice_amount = float(obj.invoice_amount) if obj.invoice_amount else None
        
        if obj.purchase_order:
            po = obj.purchase_order
            # Get the latest payment for this purchase order
            latest_payment = po.payments.order_by('-payment_date').first()
            
            return {
                'invoice_amount': invoice_amount,
                'payment_amount': float(latest_payment.amount) if latest_payment else None,
                'payment_date': latest_payment.payment_date.isoformat() if latest_payment else None,
                'payment_method': latest_payment.payment_method if latest_payment else None,
                'due_date': po.due_date.isoformat() if po.due_date else None,
            }
        
        # Retourner les informations même sans PurchaseOrder
        return {
            'invoice_amount': invoice_amount,
            'payment_amount': None,
            'payment_date': None,
            'payment_method': None,
            'due_date': None,
        }

    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'store', 'store_name',
            'movement_type', 'movement_type_display','supplier', 'supplier_name', 'customer_name', 'unit_cost', 'quantity',
            'total_value', 'invoice_amount', 'receipt_number', 'reference', 'destination_store', 'destination_store_name',
            'purchase_order', 'purchase_order_number', 'invoice', 'payment_info',
            'is_debt', 'due_date', 'payment_amount', 'payment_date', 'payment_method',
            'notes', 'date', 'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'created_by', 'created_by_name', 'customer_name', 'payment_info']
    
    def update(self, instance, validated_data):
        """Handle update of stock movement."""
        # Pop write-only fields
        validated_data.pop('purchase_order_number', None)
        validated_data.pop('is_debt', None)
        validated_data.pop('due_date', None)
        validated_data.pop('payment_amount', None)
        validated_data.pop('payment_date', None)
        validated_data.pop('payment_method', None)
        
        # Update the instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    def validate_supplier(self, value):
        """Vérifier que le fournisseur existe."""
        if value:
            try:
                # Vérifier que le fournisseur existe et est actif
                supplier = Supplier.objects.get(id=value.id)
                if not supplier.is_active:  # Si vous avez un champ is_active
                    raise serializers.ValidationError(
                        f"Le fournisseur '{supplier.name}' existe mais est inactif. "
                        "Veuillez l'activer ou choisir un autre fournisseur."
                    )
            except Supplier.DoesNotExist:
                raise serializers.ValidationError(
                    "Le fournisseur sélectionné n'existe pas. "
                    "Veuillez d'abord créer le fournisseur avant de l'utiliser."
                )
        return value
    
    def validate(self, data):
        """Validation globale des données."""
        movement_type = data.get('movement_type')
        supplier = data.get('supplier')
        destination_store = data.get('destination_store')
        store = data.get('store')
        purchase_order_number = data.get('purchase_order_number')
        payment_amount = data.get('payment_amount')
        product = data.get('product')
        quantity = data.get('quantity')
        
        # Montant versé obligatoire pour les entrées en stock
        if movement_type == 'in' and payment_amount is None:
            raise serializers.ValidationError({
                'payment_amount': (
                    'Le montant versé est obligatoire pour les entrées en stock. '
                    'Indiquez 0 si aucun paiement n\'a été effectué (dette totale) '
                    'ou le montant exact versé au fournisseur.'
                )
            })
        
        # Vérifier la quantité disponible pour les sorties et transferts
        if movement_type in ['out', 'transfer'] and product and store and quantity:
            try:
                stock = Stock.objects.get(product=product, store=store)
                available_quantity = stock.quantity - (stock.reserved_quantity or 0)
                
                if quantity > available_quantity:
                    raise serializers.ValidationError({
                        'quantity': (
                            f'Quantité insuffisante en stock. '
                            f'Disponible: {available_quantity}, '
                            f'Demandé: {quantity}. '
                            f'Produit: {product.name}, Magasin: {store.name}.'
                        )
                    })
            except Stock.DoesNotExist:
                raise serializers.ValidationError({
                    'product': (
                        f'Le produit "{product.name}" n\'existe pas dans le magasin "{store.name}". '
                        f'Quantité disponible: 0. Impossible de faire une sortie ou un transfert.'
                    )
                })

        # If purchase_order_number provided, ensure it's a non-empty string
        if purchase_order_number is not None and purchase_order_number == '':
            raise serializers.ValidationError({'purchase_order_number': 'Valeur invalide.'})

        # Valider que la PurchaseOrder appartient au même tenant (automatique via django-tenants)
        if purchase_order_number:
            try:
                po = PurchaseOrder.objects.get(order_number=purchase_order_number)
                # Vérifier que le supplier de la PO correspond au supplier du mouvement
                if po.supplier != supplier:
                    raise serializers.ValidationError({
                        'purchase_order_number': (
                            'La PurchaseOrder spécifiée appartient à un fournisseur différent. '
                            'Veuillez vérifier que le fournisseur correspond.'
                        )
                    })
            except PurchaseOrder.DoesNotExist:
                # C'est OK, une nouvelle PO sera créée lors de create()
                pass

        return data 

    def create(self, validated_data, **kwargs):
        # Pop payment/debt related write-only fields so they are not passed to StockMovement
        purchase_order_number = validated_data.pop('purchase_order_number', None)
        invoice_amount_value = validated_data.get('invoice_amount')  # Garder invoice_amount dans validated_data
        payment_amount = validated_data.pop('payment_amount', None)
        payment_date = validated_data.pop('payment_date', None)
        payment_method = validated_data.pop('payment_method', '')
        is_debt = validated_data.pop('is_debt', False)
        due_date = validated_data.pop('due_date', None)

        # Ensure decimal math uses the provided unit_cost/quantity
        unit_cost = validated_data.get('unit_cost')
        quantity = validated_data.get('quantity')
        try:
            unit_dec = Decimal(str(unit_cost)) if unit_cost is not None else None
        except Exception:
            unit_dec = None
        try:
            qty_dec = Decimal(str(quantity)) if quantity is not None else None
        except Exception:
            qty_dec = None

        po = None
        supplier = validated_data.get('supplier')
        movement_type = validated_data.get('movement_type')
        
        # Créer automatiquement un PurchaseOrder pour les entrées en stock avec fournisseur
        if movement_type == 'in' and supplier:
            with transaction.atomic():
                store = validated_data.get('store')
                
                # Si un purchase_order_number est fourni, essayer de le récupérer
                if purchase_order_number:
                    try:
                        po = PurchaseOrder.objects.get(order_number=purchase_order_number)
                    except PurchaseOrder.DoesNotExist:
                        # Créer avec le numéro fourni
                        pass
                
                # Si pas de PO trouvé, en créer un nouveau
                if not po:
                    # Générer un numéro automatique si non fourni
                    if not purchase_order_number:
                        last_po = PurchaseOrder.objects.filter(
                            order_number__startswith='PO-'
                        ).order_by('-order_number').first()
                        
                        if last_po and last_po.order_number.startswith('PO-'):
                            try:
                                last_num = int(last_po.order_number.split('-')[1])
                                purchase_order_number = f'PO-{str(last_num + 1).zfill(6)}'
                            except:
                                purchase_order_number = f'PO-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                        else:
                            purchase_order_number = f'PO-000001'
                    
                    # Créer le PurchaseOrder
                    # Utiliser invoice_amount si fourni, sinon calculer depuis unit_cost * quantity
                    if invoice_amount_value:
                        total_amt = Decimal(str(invoice_amount_value))
                    elif unit_dec is not None and qty_dec is not None:
                        total_amt = unit_dec * qty_dec
                    else:
                        total_amt = Decimal('0')
                    
                    po = PurchaseOrder.objects.create(
                        order_number=purchase_order_number,
                        supplier=supplier,
                        store=store,
                        order_date=timezone.now().date(),
                        status='received',
                        subtotal=total_amt,
                        tax_amount=Decimal('0'),
                        total_amount=total_amt,
                        paid_amount=Decimal('0'),
                        due_date=due_date or None,
                    )

                    # Créer une ligne de commande pour le produit
                    try:
                        PurchaseOrderLine.objects.create(
                            purchase_order=po,
                            product=validated_data.get('product'),
                            quantity=qty_dec or 0,
                            unit_price=unit_dec or 0,
                        )
                    except Exception:
                        pass

                # Mettre à jour la date d'échéance si fournie
                if po and due_date:
                    po.due_date = due_date
                    po.save()

                # Enregistrer le paiement si un montant est fourni
                if payment_amount:
                    try:
                        pay_amt = Decimal(str(payment_amount))
                    except Exception:
                        pay_amt = Decimal('0')

                    SupplierPayment.objects.create(
                        payment_number=f"PAY{timezone.now().strftime('%Y%m%d%H%M%S')}",
                        supplier=po.supplier,
                        purchase_order=po,
                        payment_date=payment_date or timezone.now().date(),
                        amount=pay_amt,
                        payment_method=payment_method or 'other',
                        reference=validated_data.get('reference', ''),
                    )

                    # Note: paid_amount sera mis à jour automatiquement par le signal update_purchase_order_paid_amount

                # Attacher le PurchaseOrder au mouvement de stock
                validated_data['purchase_order'] = po

        # Attach created_by if passed from view.perform_create
        created_by = kwargs.get('created_by')
        if created_by is not None:
            validated_data['created_by'] = created_by

        # Create movement
        return StockMovement.objects.create(**validated_data)

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
    products = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = [
            'id', 'transfer_number', 'reference', 'source_store', 'source_store_name',
            'destination_store', 'destination_store_name', 'status',
            'status_display', 'transfer_date', 'lines_count', 'products', 'created_at'
        ]
    
    def get_products(self, obj):
        """Get list of product names in this transfer."""
        return list(obj.lines.values_list('product__name', flat=True))


class StockTransferDetailSerializer(serializers.ModelSerializer):
    """Serializer for StockTransfer detail view."""
    
    source_store_name = serializers.CharField(source='source_store.name', read_only=True)
    destination_store_name = serializers.CharField(source='destination_store.name', read_only=True)
    source_store_detail = StoreMinimalSerializer(source='source_store', read_only=True)
    destination_store_detail = StoreMinimalSerializer(source='destination_store', read_only=True)
    lines = StockTransferLineSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = [
            'id', 'transfer_number', 'reference', 'source_store', 'source_store_name', 'source_store_detail',
            'destination_store', 'destination_store_name', 'destination_store_detail', 'status',
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
            'transfer_number', 'reference', 'source_store', 'destination_store', 'transfer_date',
            'expected_arrival', 'status', 'notes', 'lines'
        ]
        read_only_fields = ['transfer_number']
    
    def validate(self, data):
        """Valider que les quantités demandées sont disponibles."""
        source_store = data.get('source_store')
        lines_data = data.get('lines', [])
        
        errors = []
        for idx, line_data in enumerate(lines_data):
            product = line_data.get('product')
            quantity_requested = line_data.get('quantity_requested', 0)
            
            if product and source_store and quantity_requested > 0:
                try:
                    stock = Stock.objects.get(product=product, store=source_store)
                    available = stock.quantity - (stock.reserved_quantity or 0)
                    
                    if quantity_requested > available:
                        errors.append(
                            f"Ligne {idx + 1}: {product.name} - "
                            f"Disponible: {available}, Demandé: {quantity_requested}"
                        )
                except Stock.DoesNotExist:
                    errors.append(
                        f"Ligne {idx + 1}: {product.name} - "
                        f"Produit non disponible dans le magasin source (stock = 0)"
                    )
        
        if errors:
            raise serializers.ValidationError({
                'lines': [
                    'Stock insuffisant pour le transfert:',
                    *errors
                ]
            })
        
        return data
    
    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        
        # Generate transfer number
        from django.utils import timezone
        count = StockTransfer.objects.filter(
            created_at__year=timezone.now().year
        ).count() + 1
        validated_data['transfer_number'] = f"TR{timezone.now().year}{count:05d}"
        
        # Si le statut est in_transit, mettre à jour les stocks automatiquement
        status = validated_data.get('status', 'draft')
        
        transfer = StockTransfer.objects.create(**validated_data)
        
        # Create lines
        for line_data in lines_data:
            line = StockTransferLine.objects.create(transfer=transfer, **line_data)
            
            # Si le transfert est directement en transit, déduire du stock source et ajouter au stock destination
            if status == 'in_transit':
                line.quantity_sent = line.quantity_requested
                line.quantity_received = line.quantity_requested
                line.save()
                
                from apps.inventory.models import Stock
                
                # Déduire du stock source
                try:
                    stock_source = Stock.objects.get(
                        product=line.product,
                        store=transfer.source_store
                    )
                    stock_source.quantity -= line.quantity_sent
                    stock_source.save()
                except Stock.DoesNotExist:
                    pass
                
                # Ajouter au stock destination
                try:
                    stock_dest = Stock.objects.get(
                        product=line.product,
                        store=transfer.destination_store
                    )
                    stock_dest.quantity += line.quantity_received
                    stock_dest.save()
                except Stock.DoesNotExist:
                    # Créer le stock si inexistant
                    Stock.objects.create(
                        product=line.product,
                        store=transfer.destination_store,
                        quantity=line.quantity_received
                    )
        
        # Marquer le transfert comme reçu automatiquement
        if status == 'in_transit':
            transfer.status = 'received'
            transfer.actual_arrival = timezone.now().date()
            transfer.save()
        
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