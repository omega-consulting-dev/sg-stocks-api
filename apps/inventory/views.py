"""
Inventory views for API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import HasModulePermission
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Sum, F, Q
from django.utils import timezone

from core.utils.export_utils import ExcelExporter, PDFExporter
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch
import io
import csv
from django.http import HttpResponse

from apps.inventory.models import (
    Store, Stock, StockMovement, StockTransfer, 
    StockTransferLine, Inventory, InventoryLine
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
    
    queryset = Store.objects.select_related('manager')
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


@extend_schema_view(
    list=extend_schema(summary="Liste des mouvements", tags=["Inventory"]),
    retrieve=extend_schema(summary="Détail d'un mouvement", tags=["Inventory"]),
    create=extend_schema(summary="Créer un mouvement", tags=["Inventory"]),
)
class StockMovementViewSet(viewsets.ModelViewSet):
    """ViewSet for StockMovement model."""
    
    queryset = StockMovement.objects.select_related(
        'product', 'store', 'destination_store', 'created_by'
    )
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'store', 'movement_type']
    search_fields = ['product__name', 'reference']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'head', 'options']
    
    def perform_create(self, serializer):
        movement = serializer.save(created_by=self.request.user)
        self._update_stock(movement)
    
    @extend_schema(summary="Exporter les mouvements en Excel", tags=["Inventory"])
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export stock movements to Excel. Supports date filtering via query params: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD)."""
        movements = self.filter_queryset(self.get_queryset())
        
        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
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
        
        wb, ws = ExcelExporter.create_workbook("Mouvements de Stock")
        
        columns = [
            'Date', 'Référence', 'Produit', 'Magasin', 'Type', 
            'Quantité', 'Destination', 'Créé par', 'Notes'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, movement in enumerate(movements, 2):
            ws.cell(row=row_num, column=1, value=movement.created_at.strftime('%Y-%m-%d %H:%M'))
            ws.cell(row=row_num, column=2, value=movement.reference)
            ws.cell(row=row_num, column=3, value=movement.product.name)
            ws.cell(row=row_num, column=4, value=movement.store.name)
            ws.cell(row=row_num, column=5, value=movement.get_movement_type_display())
            ws.cell(row=row_num, column=6, value=float(movement.quantity))
            ws.cell(row=row_num, column=7, value=movement.destination_store.name if movement.destination_store else '')
            ws.cell(row=row_num, column=8, value=movement.created_by.username if movement.created_by else '')
            ws.cell(row=row_num, column=9, value=movement.notes or '')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"mouvements_stock_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)
    
    @extend_schema(summary="Exporter les mouvements en PDF", tags=["Inventory"])
    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        """Export stock movements to PDF. Supports date filtering via query params: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD)."""
        movements = self.filter_queryset(self.get_queryset())
        
        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
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
        
        movements = movements[:100]
        
        buffer = io.BytesIO()
        doc = PDFExporter.create_document(buffer)
        styles = PDFExporter.get_styles()
        story = []
        
        story.append(Paragraph("Mouvements de Stock", styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        date_str = timezone.now().strftime('%d/%m/%Y %H:%M')
        story.append(Paragraph(f"Généré le: {date_str}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        data = [['Date', 'Référence', 'Produit', 'Magasin', 'Type', 'Quantité']]
        for movement in movements:
            data.append([
                movement.created_at.strftime('%d/%m/%Y'),
                movement.reference,
                movement.product.name[:30],
                movement.store.name,
                movement.get_movement_type_display(),
                str(movement.quantity)
            ])
        
        table = PDFExporter.create_table(data)
        story.append(table)
        
        doc.build(story)
        
        filename = f"mouvements_stock_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return PDFExporter.generate_response(buffer, filename)
    
    @extend_schema(summary="Exporter les mouvements en CSV", tags=["Inventory"])
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export stock movements to CSV. Supports date filtering via query params: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD)."""
        movements = self.filter_queryset(self.get_queryset())
        
        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
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
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mouvements_stock.csv"'
        
        writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        writer.writerow(['Date', 'Référence', 'Produit', 'Magasin', 'Type', 'Quantité', 'Destination', 'Notes'])
        
        for movement in movements:
            writer.writerow([
                movement.created_at.strftime('%Y-%m-%d %H:%M'),
                movement.reference,
                movement.product.name,
                movement.store.name,
                movement.get_movement_type_display(),
                str(movement.quantity),
                movement.destination_store.name if movement.destination_store else '',
                movement.notes or ''
            ])
        
        return response
    
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
            stock.quantity -= movement.quantity
        
        stock.save()


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
    search_fields = ['transfer_number']
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
    
    @extend_schema(summary="Valider le transfert", tags=["Inventory"])
    @action(detail=True, methods=['post'])
    def validate_transfer(self, request, pk=None):
        """Validate and send transfer."""
        transfer = self.get_object()
        
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
