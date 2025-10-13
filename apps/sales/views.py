from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Sum, Count
from django.utils import timezone

from core.utils.export_utils import ExcelExporter, PDFExporter

from apps.sales.models import Sale, Quote, SaleLine
from apps.sales.serializers import (
    SaleListSerializer, SaleDetailSerializer, SaleCreateSerializer,
    QuoteSerializer
)


@extend_schema_view(
    list=extend_schema(summary="Liste des ventes", tags=["Sales"]),
    retrieve=extend_schema(summary="Détail d'une vente", tags=["Sales"]),
    create=extend_schema(summary="Créer une vente", tags=["Sales"]),
)
class SaleViewSet(viewsets.ModelViewSet):
    """ViewSet for Sale model."""
    
    queryset = Sale.objects.select_related('customer', 'store').prefetch_related('lines')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'store', 'status', 'payment_status', 'sale_date']
    search_fields = ['sale_number', 'customer__username']
    ordering_fields = ['sale_date', 'total_amount', 'created_at']
    ordering = ['-sale_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SaleListSerializer
        elif self.action == 'create':
            return SaleCreateSerializer
        return SaleDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @extend_schema(summary="Valider une vente", tags=["Sales"])
    @action(detail=True, methods=['post'])
    def validate_sale(self, request, pk=None):
        """Validate sale and update stock."""
        sale = self.get_object()
        
        if sale.status != 'draft':
            return Response(
                {'error': 'Seules les ventes en brouillon peuvent être validées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Decrease stock for products
        from apps.inventory.models import Stock
        for line in sale.lines.filter(line_type='product'):
            try:
                stock = Stock.objects.get(product=line.product, store=sale.store)
                if stock.available_quantity < line.quantity:
                    return Response(
                        {'error': f'Stock insuffisant pour {line.product.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                stock.quantity -= line.quantity
                stock.save()
            except Stock.DoesNotExist:
                return Response(
                    {'error': f'Aucun stock pour {line.product.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        sale.status = 'confirmed'
        sale.save()
        
        serializer = self.get_serializer(sale)
        return Response(serializer.data)
    
    @extend_schema(summary="Annuler une vente", tags=["Sales"])
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a sale."""
        sale = self.get_object()
        
        if sale.status == 'completed':
            return Response(
                {'error': 'Une vente terminée ne peut pas être annulée.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sale.status = 'cancelled'
        sale.save()
        
        serializer = self.get_serializer(sale)
        return Response(serializer.data)
    
    @extend_schema(summary="Statistiques des ventes", tags=["Sales"])
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get sales statistics."""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        stats = {
            'today': Sale.objects.filter(sale_date=today).aggregate(
                total=Sum('total_amount'), count=Count('id')
            ),
            'this_month': Sale.objects.filter(sale_date__gte=month_start).aggregate(
                total=Sum('total_amount'), count=Count('id')
            ),
            'pending': Sale.objects.filter(status='draft').count(),
        }
        return Response(stats)
    
    @extend_schema(summary="Exporter les ventes en Excel", tags=["Sales"])
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export sales to Excel."""
        sales = self.filter_queryset(self.get_queryset())
        
        wb, ws = ExcelExporter.create_workbook("Ventes")
        
        columns = [
            'N° Vente', 'Date', 'Client', 'Magasin', 'Montant Total',
            'Montant Payé', 'Statut', 'Statut Paiement'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, sale in enumerate(sales, 2):
            ws.cell(row=row_num, column=1, value=sale.sale_number)
            ws.cell(row=row_num, column=2, value=sale.sale_date.strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=3, value=sale.customer.get_display_name() if sale.customer else 'N/A')
            ws.cell(row=row_num, column=4, value=sale.store.name)
            ws.cell(row=row_num, column=5, value=float(sale.total_amount))
            ws.cell(row=row_num, column=6, value=float(sale.paid_amount))
            ws.cell(row=row_num, column=7, value=sale.get_status_display())
            ws.cell(row=row_num, column=8, value=sale.get_payment_status_display())
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"ventes_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)


    @extend_schema(summary="Exporter les ventes en PDF", tags=["Sales"])
    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        """Export sales to PDF."""
        sales = self.filter_queryset(self.get_queryset())[:100]
        
        buffer = io.BytesIO()
        doc = PDFExporter.create_document(buffer)
        styles = PDFExporter.get_styles()
        story = []
        
        story.append(Paragraph("Rapport des Ventes", styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Summary
        total_amount = sum(sale.total_amount for sale in sales)
        story.append(Paragraph(f"Total: {total_amount:,.0f} XAF", styles['CustomSubtitle']))
        story.append(Spacer(1, 0.3*inch))
        
        # Table
        data = [['N° Vente', 'Date', 'Client', 'Montant', 'Statut']]
        for sale in sales:
            data.append([
                sale.sale_number,
                sale.sale_date.strftime('%d/%m/%Y'),
                sale.customer.get_display_name()[:20] if sale.customer else 'N/A',
                f"{sale.total_amount:,.0f}",
                sale.get_status_display()
            ])
        
        table = PDFExporter.create_table(data)
        story.append(table)
        
        doc.build(story)
        
        filename = f"ventes_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return PDFExporter.generate_response(buffer, filename)


@extend_schema_view(
    list=extend_schema(summary="Liste des devis", tags=["Sales"]),
    retrieve=extend_schema(summary="Détail d'un devis", tags=["Sales"]),
    create=extend_schema(summary="Créer un devis", tags=["Sales"]),
)
class QuoteViewSet(viewsets.ModelViewSet):
    """ViewSet for Quote model."""
    
    queryset = Quote.objects.select_related('customer', 'store').prefetch_related('lines')
    serializer_class = QuoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'store', 'status']
    search_fields = ['quote_number', 'customer__username']
    ordering_fields = ['quote_date', 'created_at']
    ordering = ['-quote_date']
    
    @extend_schema(summary="Convertir en vente", tags=["Sales"])
    @action(detail=True, methods=['post'])
    def convert_to_sale(self, request, pk=None):
        """Convert quote to sale."""
        quote = self.get_object()
        
        if quote.status != 'accepted':
            return Response(
                {'error': 'Seuls les devis acceptés peuvent être convertis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create sale from quote
        sale_data = {
            'customer': quote.customer,
            'store': quote.store,
            'sale_date': timezone.now().date(),
            'discount_amount': quote.discount_amount,
            'notes': f"Créé depuis devis {quote.quote_number}",
        }
        
        sale = Sale.objects.create(**sale_data, created_by=request.user)
        
        # Copy lines
        for quote_line in quote.lines.all():
            SaleLine.objects.create(
                sale=sale,
                line_type=quote_line.line_type,
                product=quote_line.product,
                service=quote_line.service,
                description=quote_line.description,
                quantity=quote_line.quantity,
                unit_price=quote_line.unit_price,
                tax_rate=quote_line.tax_rate,
                discount_percentage=quote_line.discount_percentage,
            )
        
        sale.calculate_totals()
        sale.save()
        
        # Link quote to sale
        quote.sale = sale
        quote.save()
        
        from apps.sales.serializers import SaleDetailSerializer
        serializer = SaleDetailSerializer(sale)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
