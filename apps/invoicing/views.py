from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import HasModulePermission
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import HttpResponse

from apps.invoicing.models import Invoice, InvoicePayment
from apps.invoicing.serializers import (
    InvoiceListSerializer, InvoiceDetailSerializer, InvoiceCreateSerializer,
    InvoicePaymentSerializer
)


@extend_schema_view(
    list=extend_schema(summary="Liste des factures", tags=["Invoicing"]),
    retrieve=extend_schema(summary="Détail d'une facture", tags=["Invoicing"]),
    create=extend_schema(summary="Créer une facture", tags=["Invoicing"]),
)
class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Invoice model."""
    
    queryset = Invoice.objects.select_related('customer', 'sale').prefetch_related('lines', 'payments')
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'invoicing'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'status', 'invoice_date']
    search_fields = ['invoice_number', 'customer__username']
    ordering_fields = ['invoice_date', 'due_date', 'total_amount']
    ordering = ['-invoice_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        elif self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @extend_schema(summary="Envoyer une facture par email", tags=["Invoicing"])
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """Send invoice by email."""
        invoice = self.get_object()
        
        if invoice.status == 'draft':
            return Response(
                {'error': 'Les factures en brouillon ne peuvent pas être envoyées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Implement actual email sending
        invoice.status = 'sent'
        invoice.save()
        
        return Response({'message': 'Facture envoyée par email'})
    
    @extend_schema(summary="Générer le PDF d'une facture", tags=["Invoicing"])
    @action(detail=True, methods=['get'])
    def generate_pdf(self, request, pk=None):
        """Generate invoice PDF."""
        invoice = self.get_object()
        
        buffer = invoice.generate_pdf()
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture_{invoice.invoice_number}.pdf"'
        return response
    
    @extend_schema(summary="Enregistrer un paiement", tags=["Invoicing"])
    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """Record a payment for this invoice."""
        invoice = self.get_object()
        
        if invoice.status == 'cancelled':
            return Response(
                {'error': 'Impossible d\'enregistrer un paiement pour une facture annulée.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method')
        
        if not amount or float(amount) <= 0:
            return Response(
                {'error': 'Montant invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if float(amount) > float(invoice.balance_due):
            return Response(
                {'error': 'Le montant dépasse le solde restant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create payment
        count = InvoicePayment.objects.filter(invoice=invoice).count() + 1
        payment = InvoicePayment.objects.create(
            payment_number=f"{invoice.invoice_number}-PAY{count:03d}",
            invoice=invoice,
            payment_date=timezone.now().date(),
            amount=amount,
            payment_method=payment_method,
            reference=request.data.get('reference', ''),
            notes=request.data.get('notes', ''),
            created_by=request.user
        )
        
        # Update invoice
        invoice.paid_amount += float(amount)
        if invoice.is_fully_paid:
            invoice.status = 'paid'
        invoice.save()
        
        serializer = InvoicePaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(summary="Statistiques des factures", tags=["Invoicing"])
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get invoice statistics."""
        stats = {
            'total': Invoice.objects.count(),
            'draft': Invoice.objects.filter(status='draft').count(),
            'sent': Invoice.objects.filter(status='sent').count(),
            'paid': Invoice.objects.filter(status='paid').count(),
            'overdue': Invoice.objects.filter(
                status__in=['sent'],
                due_date__lt=timezone.now().date()
            ).count(),
            'total_amount': Invoice.objects.aggregate(
                total=Sum('total_amount')
            )['total'] or 0,
            'paid_amount': Invoice.objects.aggregate(
                total=Sum('paid_amount')
            )['total'] or 0,
        }
        return Response(stats)


@extend_schema_view(
    list=extend_schema(summary="Liste des paiements", tags=["Invoicing"]),
)
class InvoicePaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for InvoicePayment model (read-only)."""
    
    queryset = InvoicePayment.objects.select_related('invoice', 'created_by')
    serializer_class = InvoicePaymentSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'invoicing'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['invoice', 'payment_method', 'payment_date']
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']