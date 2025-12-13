"""
Inventory views for API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import HasModulePermission
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Sum, F, Q
from django.utils import timezone
from django.http import HttpResponse
import django_filters

from core.utils.export_utils import ExcelExporter, PDFExporter
from core.mixins import StoreAccessMixin, PermissionCheckMixin, UserStoreValidationMixin
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch
import io

from apps.inventory.models import (
    Store, Stock, StockMovement, StockTransfer, 
    StockTransferLine, Inventory, InventoryLine, ReceiptNumberSequence
)
from apps.inventory.serializers import (
    StoreSerializer, StockSerializer, StockMovementSerializer,
    StockTransferListSerializer, StockTransferDetailSerializer,
    StockTransferCreateSerializer, InventoryListSerializer,
    InventoryDetailSerializer, InventoryCreateSerializer
)


@extend_schema_view(
    list=extend_schema(summary="Liste des magasins", tags=["Inventory"]),
    retrieve=extend_schema(summary="Détail d'un magasin", tags=["Inventory"]),
    create=extend_schema(summary="Créer un magasin", tags=["Inventory"]),
    update=extend_schema(summary="Modifier un magasin", tags=["Inventory"]),
)
class StoreViewSet(viewsets.ModelViewSet):
    """ViewSet for Store model."""
    
    queryset = Store.objects.filter(is_active=True).select_related('manager')
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store_type', 'is_active']
    search_fields = ['name', 'code', 'city']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    def perform_destroy(self, instance):
        """Soft delete: désactiver au lieu de supprimer."""
        instance.is_active = False
        instance.updated_by = self.request.user
        instance.save()
    
    @extend_schema(summary="Statistiques d'un magasin", tags=["Inventory"])
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get store statistics."""
        store = self.get_object()
        stats = {
            'total_products': store.stocks.count(),
            'total_stock_value': store.stocks.aggregate(
                total=Sum(F('quantity') * F('product__cost_price'))
            )['total'] or 0,
            'low_stock_items': store.stocks.filter(
                quantity__lt=F('product__minimum_stock')
            ).count(),
        }
        return Response(stats)
    
    @extend_schema(
        summary="Liste des produits d'un magasin",
        description="Récupère tous les produits présents dans un magasin avec leur stock.",
        tags=["Inventory"]
    )
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products in a store with their stock information."""
        store = self.get_object()
        
        # Récupérer tous les stocks de ce magasin avec les infos produits
        stocks = Stock.objects.filter(store=store).select_related(
            'product', 'product__category'
        ).order_by('product__name')
        
        # Préparer les données
        products_data = []
        for stock in stocks:
            product = stock.product
            products_data.append({
                'product_id': product.id,
                'product_name': product.name,
                'product_reference': product.reference,
                'category': product.category.name if product.category else None,
                'quantity': float(stock.quantity),
                'reserved_quantity': float(stock.reserved_quantity),
                'available_quantity': float(stock.available_quantity),
                'minimum_stock': product.minimum_stock,
                'optimal_stock': product.optimal_stock,
                'cost_price': float(product.cost_price) if product.cost_price else None,
                'selling_price': float(product.selling_price) if product.selling_price else None,
                'stock_status': 'low' if stock.quantity < product.minimum_stock else 'normal',
                'is_active': product.is_active,
            })
        
        return Response({
            'store': {
                'id': store.id,
                'name': store.name,
                'code': store.code,
            },
            'total_products': len(products_data),
            'products': products_data
        })


@extend_schema_view(
    list=extend_schema(summary="Liste des stocks", tags=["Inventory"]),
    retrieve=extend_schema(summary="Détail d'un stock", tags=["Inventory"]),
)
class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Stock model (read-only)."""
    
    queryset = Stock.objects.select_related('product', 'store')
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'store']
    search_fields = ['product__name', 'product__reference']
    ordering_fields = ['quantity', 'created_at']
    ordering = ['-created_at']
    
    @extend_schema(summary="Produits en rupture", tags=["Inventory"])
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock items."""
        queryset = self.get_queryset().filter(
            quantity__lt=F('product__minimum_stock')
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class StockMovementFilterSet(django_filters.FilterSet):
    """Custom FilterSet for StockMovement with date range filters."""
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')
    
    class Meta:
        model = StockMovement
        fields = ['product', 'store', 'movement_type', 'supplier', 'date_from', 'date_to']


@extend_schema_view(
    list=extend_schema(summary="Liste des mouvements", tags=["Inventory"]),
    retrieve=extend_schema(summary="Détail d'un mouvement", tags=["Inventory"]),
    create=extend_schema(summary="Créer un mouvement", tags=["Inventory"]),
)
class StockMovementViewSet(StoreAccessMixin, UserStoreValidationMixin, viewsets.ModelViewSet):
    """ViewSet for StockMovement model with automatic store filtering."""
    
    queryset = StockMovement.objects.filter(is_active=True).select_related(
        'product', 'store', 'destination_store','supplier', 'created_by', 'purchase_order'
    ).prefetch_related('purchase_order__payments')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StockMovementFilterSet
    search_fields = ['product__name', 'reference', 'supplier__name', 'supplier__supplier_code']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    @extend_schema(summary="Obtenir le prochain numéro de pièce", tags=["Inventory"])
    @action(detail=False, methods=['get'], url_path='next-receipt-number')
    def next_receipt_number(self, request):
        """Get the next available receipt number."""
        # Récupérer le plus grand numéro existant (actif ou non) pour continuer la séquence
        all_receipts = StockMovement.objects.filter(
            receipt_number__startswith='RECEIPT-'
        ).values_list('receipt_number', flat=True)
        
        numbers = []
        for receipt in all_receipts:
            try:
                num = int(receipt.replace('RECEIPT-', ''))
                numbers.append(num)
            except (ValueError, AttributeError):
                pass
        
        next_num = max(numbers) + 1 if numbers else 1
        next_receipt = f'RECEIPT-{str(next_num).zfill(3)}'
        return Response({'next_receipt_number': next_receipt})

    
    def perform_create(self, serializer):
        movement = serializer.save(created_by=self.request.user)
        self._update_stock(movement)
    
    def perform_update(self, serializer):
        """Override to handle stock updates when modifying a movement."""
        old_instance = self.get_object()
        
        # Inverser l'ancien mouvement
        self._reverse_stock(old_instance)
        
        # Sauvegarder les modifications
        updated_instance = serializer.save(updated_by=self.request.user)
        
        # Appliquer le nouveau mouvement
        self._update_stock(updated_instance)
    
    def perform_destroy(self, instance):
        """Override to reverse stock changes and soft delete."""
        # Inverser les changements de stock avant la désactivation
        self._reverse_stock(instance)
        # Soft delete: désactiver au lieu de supprimer
        instance.is_active = False
        instance.updated_by = self.request.user
        instance.save()
    
    def _reverse_stock(self, movement):
        """Reverse stock changes when deleting a movement."""
        try:
            stock = Stock.objects.get(
                product=movement.product,
                store=movement.store
            )
            
            if movement.movement_type == 'in':
                # Inverser une entrée: soustraire la quantité
                if stock.quantity < movement.quantity:
                    raise ValidationError(
                        f"Impossible de supprimer cette entrée. Le stock actuel ({stock.quantity}) "
                        f"est inférieur à la quantité de l'entrée ({movement.quantity}). "
                        "Des sorties ont probablement été effectuées depuis cette entrée."
                    )
                stock.quantity -= movement.quantity
                stock.save()
            elif movement.movement_type == 'out':
                # Inverser une sortie: ajouter la quantité
                stock.quantity += movement.quantity
                stock.save()
            elif movement.movement_type == 'transfer':
                # Inverser un transfert: rajouter au stock source et retirer de la destination
                stock.quantity += movement.quantity
                stock.save()
                
                if movement.destination_store:
                    try:
                        dest_stock = Stock.objects.get(
                            product=movement.product,
                            store=movement.destination_store
                        )
                        if dest_stock.quantity < movement.quantity:
                            raise ValidationError(
                                f"Impossible de supprimer ce transfert. Le stock destination ({dest_stock.quantity}) "
                                f"est inférieur à la quantité transférée ({movement.quantity})."
                            )
                        dest_stock.quantity -= movement.quantity
                        dest_stock.save()
                    except Stock.DoesNotExist:
                        pass
        except Stock.DoesNotExist:
            # Si le stock n'existe pas, on ne peut pas inverser
            raise ValidationError(
                "Impossible de supprimer ce mouvement. Le stock associé n'existe plus."
            )
     
    def _update_stock(self, movement):
        """Update stock based on movement type."""
        stock, _ = Stock.objects.get_or_create(
            product=movement.product,
            store=movement.store,
            defaults={'quantity': 0, 'reserved_quantity': 0}
        )
        
        if movement.movement_type == 'in':
            stock.quantity += movement.quantity
        elif movement.movement_type == 'out':
            # Vérification supplémentaire (normalement déjà validé par le serializer)
            if stock.quantity < movement.quantity:
                raise ValidationError(
                    f"Stock insuffisant pour {movement.product.name} dans {movement.store.name}. "
                    f"Disponible: {stock.quantity}, Demandé: {movement.quantity}"
                )
            stock.quantity -= movement.quantity
        elif movement.movement_type == 'transfer':
            # Pour les transferts, diminuer le stock source
            if stock.quantity < movement.quantity:
                raise ValidationError(
                    f"Stock insuffisant pour transférer {movement.product.name}. "
                    f"Disponible: {stock.quantity}, Demandé: {movement.quantity}"
                )
            stock.quantity -= movement.quantity
            
            # Augmenter le stock destination si spécifié
            if movement.destination_store:
                dest_stock, _ = Stock.objects.get_or_create(
                    product=movement.product,
                    store=movement.destination_store,
                    defaults={'quantity': 0, 'reserved_quantity': 0}
                )
                dest_stock.quantity += movement.quantity
                dest_stock.save()
        
        stock.save()

    @extend_schema(summary="Exporter les mouvements en Excel", tags=["Inventory"])
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export stock movements to Excel with filtering.
        Supports all filters from the list endpoint:
        - movement_type: 'in', 'out', 'transfer'
        - date_from: YYYY-MM-DD (applies to created_at)
        - date_to: YYYY-MM-DD (applies to created_at)
        - supplier: supplier id
        - product: product id
        - store: store id
        - search: search in product name, reference, supplier name, supplier code
        """
        # Use filter_queryset to apply all configured filters (DjangoFilterBackend, SearchFilter, etc.)
        movements = self.filter_queryset(self.get_queryset())
        
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
        import openpyxl
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Mouvements"
        
        columns = [
            'Date', 'Référence', 'Produit', 'Magasin', 'Fournisseur', 'Type', 
            'Quantité', 'Coût Unitaire', 'Destination', 'PO Number', 'Créé par', 'Notes'
        ]
        
        # Style header
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for col_num, col_title in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = col_title
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Add data
        for row_num, movement in enumerate(movements, 2):
            ws.cell(row=row_num, column=1, value=movement.created_at.strftime('%Y-%m-%d %H:%M'))
            ws.cell(row=row_num, column=2, value=movement.reference)
            ws.cell(row=row_num, column=3, value=movement.product.name)
            ws.cell(row=row_num, column=4, value=movement.store.name)
            ws.cell(row=row_num, column=5, value=movement.supplier.name if movement.supplier else '')
            ws.cell(row=row_num, column=6, value=movement.get_movement_type_display())
            ws.cell(row=row_num, column=7, value=float(movement.quantity))
            ws.cell(row=row_num, column=8, value=float(movement.unit_cost or 0))
            ws.cell(row=row_num, column=9, value=movement.destination_store.name if movement.destination_store else '')
            ws.cell(row=row_num, column=10, value=movement.purchase_order.order_number if movement.purchase_order else '')
            ws.cell(row=row_num, column=11, value=movement.created_by.username if movement.created_by else '')
            ws.cell(row=row_num, column=12, value=movement.notes or '')
        
        # Auto adjust columns
        for col_num, col_title in enumerate(columns, 1):
            ws.column_dimensions[get_column_letter(col_num)].width = 18
        
        # Generate response
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = f"mouvements_stock_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        
        return response
    
    @extend_schema(summary="Exporter les mouvements en PDF", tags=["Inventory"])
    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        """Export stock movements to PDF with filtering.
        Supports all filters from the list endpoint:
        - movement_type: 'in', 'out', 'transfer'
        - date_from: YYYY-MM-DD (applies to created_at)
        - date_to: YYYY-MM-DD (applies to created_at)
        - supplier: supplier id
        - product: product id
        - store: store id
        - search: search in product name, reference, supplier name, supplier code
        """
        # Use filter_queryset to apply all configured filters
        movements = self.filter_queryset(self.get_queryset())
        
        # Get filter parameters
        movement_type = request.query_params.get('movement_type', '')
        date_from = request.query_params.get('date_from', '')
        date_to = request.query_params.get('date_to', '')
        
        # Apply date filters if provided
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                movements = movements.filter(created_at__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                movements = movements.filter(created_at__date__lte=date_to_obj)
            except ValueError:
                pass
        
        # Limit to 100 records for PDF
        movements = movements[:100]
        
        # Import necessary libraries
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from datetime import datetime
        from django.utils import timezone
        import io
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=50,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#366092'),
            spaceAfter=20,
            alignment=1  # Center alignment
        )
        
        # Generate title with type filter if present
        type_label = f" - {movement_type.upper()}" if movement_type else ""
        title = Paragraph(f"Mouvements de Stock{type_label}", title_style)
        elements.append(title)
        
        # Date range and generation info
        date_range = f"Du {date_from} au {date_to}" if date_from and date_to else "Tous les mouvements"
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=1
        )
        date_text = Paragraph(
            f"{date_range} - Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}", 
            date_style
        )
        elements.append(date_text)
        elements.append(Spacer(1, 0.3*inch))
        
        # Table data
        data = [['Date', 'Référence', 'Produit', 'Fournisseur', 'Type', 'Quantité', 'Coût Unit.', 'Magasin']]
        
        for movement in movements:
            row = [
                movement.created_at.strftime('%d/%m/%Y'),
                movement.reference[:15] if movement.reference else '-',
                movement.product.name[:25],
                (movement.supplier.name[:15] if movement.supplier else '-'),
                movement.get_movement_type_display(),
                str(movement.quantity),
                f"{movement.unit_cost or 0:.2f}",
                movement.store.name[:15]
            ]
            data.append(row)
        
        # Create table
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            
            # Body style
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
        
        # Statistics
        elements.append(Spacer(1, 0.3*inch))
        total_qty = sum(m.quantity for m in movements)
        total_value = sum((m.unit_cost or 0) * m.quantity for m in movements)
        
        stats_text = f"<b>Total mouvements:</b> {movements.count()} | <b>Quantité totale:</b> {total_qty} | <b>Valeur totale:</b> {total_value:.2f} FCFA"
        stats = Paragraph(stats_text, date_style)
        elements.append(stats)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Generate response
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        filename = f'mouvements_stock_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    


@extend_schema_view(
    list=extend_schema(summary="Liste des transferts", tags=["Inventory"]),
    retrieve=extend_schema(summary="Détail d'un transfert", tags=["Inventory"]),
    create=extend_schema(summary="Créer un transfert", tags=["Inventory"]),
)
class StockTransferViewSet(viewsets.ModelViewSet):
    """ViewSet for StockTransfer model."""
    
    queryset = StockTransfer.objects.select_related(
        'source_store', 'destination_store'
    ).prefetch_related('lines__product')
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source_store', 'destination_store', 'status']
    search_fields = ['transfer_number', 'source_store__name', 'destination_store__name', 'lines__product__name']
    ordering_fields = ['transfer_date', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StockTransferListSerializer
        elif self.action == 'create':
            return StockTransferCreateSerializer
        return StockTransferDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def _can_validate_transfer(self, transfer):
        """Vérifier si l'utilisateur peut valider le transfert (envoi)."""
        user = self.request.user
        
        # Admin peut tout faire
        if user.is_superuser or user.role.name == 'super_admin':
            return True
        
        # Doit avoir la permission de gérer l'inventaire
        if not user.role.can_manage_inventory:
            return False
        
        # Doit être assigné au store source
        if user.role.access_scope == 'assigned':
            return transfer.source_store in user.assigned_stores.all()
        
        return True
    
    def _can_receive_transfer(self, transfer):
        """Vérifier si l'utilisateur peut recevoir le transfert."""
        user = self.request.user
        
        # Admin peut tout faire
        if user.is_superuser or user.role.name == 'super_admin':
            return True
        
        # Doit avoir la permission de voir/gérer l'inventaire
        if not (user.role.can_manage_inventory or user.role.can_view_inventory):
            return False
        
        # Doit être assigné au store destination
        if user.role.access_scope == 'assigned':
            return transfer.destination_store in user.assigned_stores.all()
        
        return True
    
    @extend_schema(summary="Valider le transfert", tags=["Inventory"])
    @action(detail=True, methods=['post'])
    def validate_transfer(self, request, pk=None):
        """Validate and send transfer."""
        transfer = self.get_object()
        
        # Vérifier les permissions
        if not self._can_validate_transfer(transfer):
            return Response(
                {'error': 'Vous n\'avez pas la permission de valider ce transfert. Vous devez être assigné au magasin source.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if transfer.status != 'draft':
            return Response(
                {'error': 'Seuls les transferts en brouillon peuvent être validés.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update quantities sent
        for line in transfer.lines.all():
            line.quantity_sent = line.quantity_requested
            line.save()
            
            # Decrease stock in source
            stock = Stock.objects.get(
                product=line.product,
                store=transfer.source_store
            )
            stock.quantity -= line.quantity_sent
            stock.save()
        
        transfer.status = 'in_transit'
        transfer.validated_by = request.user
        transfer.save()
        
        serializer = self.get_serializer(transfer)
        return Response(serializer.data)
    
    @extend_schema(summary="Recevoir le transfert", tags=["Inventory"])
    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Receive transfer."""
        transfer = self.get_object()
        
        # Vérifier les permissions
        if not self._can_receive_transfer(transfer):
            return Response(
                {'error': 'Vous n\'avez pas la permission de recevoir ce transfert. Vous devez être assigné au magasin destination.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if transfer.status != 'in_transit':
            return Response(
                {'error': 'Ce transfert ne peut pas être reçu.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update quantities received
        for line in transfer.lines.all():
            line.quantity_received = line.quantity_sent
            line.save()
            
            # Increase stock in destination
            stock, _ = Stock.objects.get_or_create(
                product=line.product,
                store=transfer.destination_store,
                defaults={'quantity': 0, 'reserved_quantity': 0}
            )
            stock.quantity += line.quantity_received
            stock.save()
        
        transfer.status = 'received'
        transfer.received_by = request.user
        transfer.actual_arrival = timezone.now().date()
        transfer.save()
        
        serializer = self.get_serializer(transfer)
        return Response(serializer.data)
    
    @extend_schema(summary="Annuler le transfert", tags=["Inventory"])
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel transfer."""
        transfer = self.get_object()
        
        if transfer.status not in ['draft', 'in_transit']:
            return Response(
                {'error': 'Ce transfert ne peut pas être annulé.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si le transfert était en transit, remettre le stock au magasin source
        if transfer.status == 'in_transit':
            for line in transfer.lines.all():
                stock = Stock.objects.get(
                    product=line.product,
                    store=transfer.source_store
                )
                stock.quantity += line.quantity_sent
                stock.save()
        
        transfer.status = 'cancelled'
        transfer.save()
        
        serializer = self.get_serializer(transfer)
        return Response(serializer.data)
    
    @extend_schema(summary="Exporter les transferts en Excel", tags=["Inventory"])
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export transfers to Excel."""
        # Récupérer les filtres
        queryset = self.filter_queryset(self.get_queryset())
        
        # Appliquer les filtres de date si présents
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(transfer_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transfer_date__lte=end_date)
        
        transfers = queryset.select_related(
            'source_store', 'destination_store', 'created_by', 
            'validated_by', 'received_by'
        ).prefetch_related('lines__product')
        
        # Créer le workbook
        wb, ws = ExcelExporter.create_workbook("Transferts de Stock")
        
        # En-têtes
        columns = [
            'N° Transfert', 'Date', 'Magasin Source', 'Magasin Destination',
            'Nombre d\'articles', 'Statut', 'Date d\'arrivée prévue', 
            'Date d\'arrivée réelle', 'Créé par', 'Validé par', 'Reçu par'
        ]
        ExcelExporter.style_header(ws, columns)
        
        # Données
        status_labels = {
            'draft': 'Brouillon',
            'pending': 'En attente',
            'in_transit': 'En transit',
            'received': 'Reçu',
            'cancelled': 'Annulé'
        }
        
        for row_num, transfer in enumerate(transfers, 2):
            ws.cell(row=row_num, column=1, value=transfer.transfer_number)
            ws.cell(row=row_num, column=2, value=transfer.transfer_date.strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=3, value=transfer.source_store.name)
            ws.cell(row=row_num, column=4, value=transfer.destination_store.name)
            ws.cell(row=row_num, column=5, value=transfer.lines.count())
            ws.cell(row=row_num, column=6, value=status_labels.get(transfer.status, transfer.status))
            ws.cell(row=row_num, column=7, value=transfer.expected_arrival.strftime('%d/%m/%Y') if transfer.expected_arrival else '')
            ws.cell(row=row_num, column=8, value=transfer.actual_arrival.strftime('%d/%m/%Y') if transfer.actual_arrival else '')
            ws.cell(row=row_num, column=9, value=transfer.created_by.get_full_name() if transfer.created_by else '')
            ws.cell(row=row_num, column=10, value=transfer.validated_by.get_full_name() if transfer.validated_by else '')
            ws.cell(row=row_num, column=11, value=transfer.received_by.get_full_name() if transfer.received_by else '')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"transferts_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)


@extend_schema_view(
    list=extend_schema(summary="Liste des inventaires", tags=["Inventory"]),
    retrieve=extend_schema(summary="Détail d'un inventaire", tags=["Inventory"]),
    create=extend_schema(summary="Créer un inventaire", tags=["Inventory"]),
)
class InventoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Inventory model."""
    
    queryset = Inventory.objects.select_related('store').prefetch_related('lines__product')
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store', 'status']
    search_fields = ['inventory_number']
    ordering_fields = ['inventory_date', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return InventoryListSerializer
        elif self.action == 'create':
            return InventoryCreateSerializer
        return InventoryDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @extend_schema(summary="Valider l'inventaire", tags=["Inventory"])
    @action(detail=True, methods=['post'])
    def validate_inventory(self, request, pk=None):
        """Validate inventory and adjust stock."""
        inventory = self.get_object()
        
        if inventory.status != 'completed':
            return Response(
                {'error': 'Seuls les inventaires terminés peuvent être validés.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Adjust stock based on differences
        for line in inventory.lines.all():
            if line.difference != 0:
                stock = Stock.objects.get(
                    product=line.product,
                    store=inventory.store
                )
                stock.quantity = line.counted_quantity
                stock.save()
                
                # Create adjustment movement
                StockMovement.objects.create(
                    product=line.product,
                    store=inventory.store,
                    movement_type='adjustment',
                    quantity=abs(line.difference),
                    reference=inventory.inventory_number,
                    notes=f"Ajustement inventaire {inventory.inventory_number}",
                    created_by=request.user
                )
        
        inventory.status = 'validated'
        inventory.validated_by = request.user
        inventory.validation_date = timezone.now()
        inventory.save()
        
        serializer = self.get_serializer(inventory)
        return Response(serializer.data)
    
    @extend_schema(summary="Exporter l'état des stocks en Excel", tags=["Inventory"])
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export stock status to Excel."""
        stocks = Stock.objects.select_related('product', 'store').all()
        
        wb, ws = ExcelExporter.create_workbook("État des Stocks")
        
        columns = [
            'Produit', 'Référence', 'Magasin', 'Quantité',
            'Quantité Réservée', 'Quantité Disponible', 'Stock Min', 'Statut'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, stock in enumerate(stocks, 2):
            ws.cell(row=row_num, column=1, value=stock.product.name)
            ws.cell(row=row_num, column=2, value=stock.product.reference)
            ws.cell(row=row_num, column=3, value=stock.store.name)
            ws.cell(row=row_num, column=4, value=float(stock.quantity))
            ws.cell(row=row_num, column=5, value=float(stock.reserved_quantity))
            ws.cell(row=row_num, column=6, value=float(stock.available_quantity))
            ws.cell(row=row_num, column=7, value=stock.product.minimum_stock)
            
            if stock.quantity < stock.product.minimum_stock:
                status = 'ALERTE'
            elif stock.quantity == 0:
                status = 'RUPTURE'
            else:
                status = 'OK'
            ws.cell(row=row_num, column=8, value=status)
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"stocks_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)
