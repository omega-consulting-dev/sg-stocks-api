from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from apps.accounts.permissions import HasModulePermission
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import HttpResponse
import io
import csv
from core.utils.export_utils import ExcelExporter, PDFExporter
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch

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
    """
    ViewSet for Invoice model with secure store-based filtering.
    - Super admin: voit toutes les factures
    - Manager (access_scope='all'): voit toutes les factures
    - Caissier/autres (access_scope='assigned'): voit uniquement les factures de leurs stores assignés
    - Utilisateur (access_scope='own'): voit uniquement ses propres factures créées
    """
    
    queryset = Invoice.objects.select_related('customer', 'store', 'sale').prefetch_related('lines', 'payments')
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'invoicing'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'store', 'status', 'invoice_date']
    search_fields = ['invoice_number', 'customer__name', 'customer__email', 'customer__customer_code']
    ordering_fields = ['invoice_date', 'due_date', 'total_amount']
    ordering = ['-invoice_date']
    
    def get_queryset(self):
        """
        Filtrage sécurisé des factures selon le rôle et les stores assignés.
        Assure qu'un utilisateur ne peut voir que les données auxquelles il a accès.
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Super admin voit tout
        if user.is_superuser:
            return queryset
        
        # Vérifier le scope d'accès du rôle
        if hasattr(user, 'role') and user.role:
            # Manager avec accès à tous les stores
            if user.role.access_scope == 'all':
                return queryset
            
            # Utilisateur avec accès uniquement aux stores assignés
            elif user.role.access_scope == 'assigned':
                # Filtrer par stores assignés à l'utilisateur
                assigned_stores = user.assigned_stores.all()
                if assigned_stores.exists():
                    return queryset.filter(store__in=assigned_stores)
                else:
                    # Si aucun store assigné, retourner queryset vide
                    return queryset.none()
            
            # Utilisateur avec accès uniquement à ses propres données
            elif user.role.access_scope == 'own':
                return queryset.filter(created_by=user)
        
        # Par défaut, filtrer par stores assignés (sécurité)
        assigned_stores = user.assigned_stores.all()
        if assigned_stores.exists():
            return queryset.filter(store__in=assigned_stores)
        
        # Si aucun rôle et aucun store, pas d'accès
        return queryset.none()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        elif self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Override create to return detailed invoice after creation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return detailed serializer with all fields including id
        invoice = serializer.instance
        detail_serializer = InvoiceDetailSerializer(invoice)
        headers = self.get_success_headers(detail_serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        """
        Validation lors de la création:
        - Si store non fourni, utiliser le premier store assigné de l'utilisateur
        - Vérifier que l'utilisateur a accès au store spécifié
        """
        user = self.request.user
        store = serializer.validated_data.get('store')
        
        # Si pas de store fourni, utiliser le premier store assigné
        if not store:
            assigned_stores = user.assigned_stores.all()
            if assigned_stores.exists():
                serializer.validated_data['store'] = assigned_stores.first()
            else:
                raise ValidationError({
                    'store': 'Aucun point de vente assigné. Veuillez spécifier un store.'
                })
        else:
            # Vérifier que l'utilisateur a accès à ce store (sauf super admin)
            if not user.is_superuser:
                if hasattr(user, 'role') and user.role and user.role.access_scope != 'all':
                    if not user.assigned_stores.filter(id=store.id).exists():
                        raise ValidationError({
                            'store': 'Vous n\'avez pas accès à ce point de vente.'
                        })
        
        serializer.save(created_by=user)
    
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
    
    @extend_schema(summary="Exporter les factures en Excel", tags=["Invoicing"])
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export invoices to Excel. Supports date filtering via query params: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD)."""
        invoices = self.filter_queryset(self.get_queryset())
        
        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                invoices = invoices.filter(invoice_date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                invoices = invoices.filter(invoice_date__lte=date_to_obj)
            except ValueError:
                pass
        
        wb, ws = ExcelExporter.create_workbook("Factures")
        
        columns = [
            'Numéro', 'Client', 'Date', 'Échéance', 'Montant Total', 
            'Montant Payé', 'Solde', 'Statut', 'Créé par'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, invoice in enumerate(invoices, 2):
            ws.cell(row=row_num, column=1, value=invoice.invoice_number)
            ws.cell(row=row_num, column=2, value=invoice.customer.name if invoice.customer else '')
            ws.cell(row=row_num, column=3, value=invoice.invoice_date.strftime('%Y-%m-%d'))
            ws.cell(row=row_num, column=4, value=invoice.due_date.strftime('%Y-%m-%d'))
            ws.cell(row=row_num, column=5, value=float(invoice.total_amount))
            ws.cell(row=row_num, column=6, value=float(invoice.paid_amount))
            ws.cell(row=row_num, column=7, value=float(invoice.balance_due))
            ws.cell(row=row_num, column=8, value=invoice.get_status_display())
            ws.cell(row=row_num, column=9, value=invoice.created_by.username if invoice.created_by else '')
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"factures_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)
    
    @extend_schema(summary="Exporter les factures en PDF", tags=["Invoicing"])
    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        """Export invoices to PDF. Supports date filtering via query params: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD)."""
        invoices = self.filter_queryset(self.get_queryset())
        
        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                invoices = invoices.filter(invoice_date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                invoices = invoices.filter(invoice_date__lte=date_to_obj)
            except ValueError:
                pass
        
        invoices = invoices[:100]
        
        buffer = io.BytesIO()
        doc = PDFExporter.create_document(buffer)
        styles = PDFExporter.get_styles()
        story = []
        
        story.append(Paragraph("Factures", styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        date_str = timezone.now().strftime('%d/%m/%Y %H:%M')
        story.append(Paragraph(f"Généré le: {date_str}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        data = [['Numéro', 'Client', 'Date', 'Montant Total', 'Statut']]
        for invoice in invoices:
            data.append([
                invoice.invoice_number,
                invoice.customer.name if invoice.customer else '',
                invoice.invoice_date.strftime('%d/%m/%Y'),
                f"{float(invoice.total_amount):,.0f}",
                invoice.get_status_display()
            ])
        
        table = PDFExporter.create_table(data)
        story.append(table)
        
        doc.build(story)
        
        filename = f"factures_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return PDFExporter.generate_response(buffer, filename)
    
    @extend_schema(summary="Exporter les factures en CSV", tags=["Invoicing"])
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export invoices to CSV. Supports date filtering via query params: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD)."""
        invoices = self.filter_queryset(self.get_queryset())
        
        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                invoices = invoices.filter(invoice_date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                invoices = invoices.filter(invoice_date__lte=date_to_obj)
            except ValueError:
                pass
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="factures.csv"'
        
        writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        writer.writerow(['Numéro', 'Client', 'Date', 'Échéance', 'Montant Total', 'Montant Payé', 'Solde', 'Statut'])
        
        for invoice in invoices:
            writer.writerow([
                invoice.invoice_number,
                invoice.customer.name if invoice.customer else '',
                invoice.invoice_date.strftime('%Y-%m-%d'),
                invoice.due_date.strftime('%Y-%m-%d'),
                f"{float(invoice.total_amount):,.2f}",
                f"{float(invoice.paid_amount):,.2f}",
                f"{float(invoice.balance_due):,.2f}",
                invoice.get_status_display()
            ])
        
        return response
    
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
    create=extend_schema(summary="Créer un paiement", tags=["Invoicing"]),
)
class InvoicePaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for InvoicePayment model."""
    
    queryset = InvoicePayment.objects.select_related('invoice')
    serializer_class = InvoicePaymentSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = 'invoicing'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['invoice', 'payment_method', 'payment_date']
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']