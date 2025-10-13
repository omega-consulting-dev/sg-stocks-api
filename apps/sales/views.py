from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Sum, Count
from django.utils import timezone

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
