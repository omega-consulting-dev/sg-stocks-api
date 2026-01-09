from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.accounts.permissions import HasModulePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Sum, Q, F
from decimal import Decimal, InvalidOperation

from core.utils.export_utils import ExcelExporter
import pandas as pd

from apps.customers.models import Customer
from apps.customers.serializers import (
    CustomerListSerializer,
    CustomerDetailSerializer,
    CustomerCreateUpdateSerializer
)
from apps.customers.filters import CustomerFilter
from apps.invoicing.models import Invoice, InvoicePayment


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Customer management with role-based filtering.
    - Super admin / Manager (access_scope='all'): voit tous les clients
    - Magasinier (access_scope='assigned'): voit les clients de ses stores
    - Caissier (access_scope='own'): voit uniquement les clients qu'il a créés ou avec qui il a fait des transactions
    """
    queryset = Customer.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ['customer_code', 'name', 'email', 'phone', 'mobile']
    ordering_fields = ['name', 'customer_code', 'created_at', 'credit_limit', 'city']
    ordering = ['name']
    
    def get_queryset(self):
        """
        Filtrage sécurisé des clients selon le rôle et access_scope.
        Tous les utilisateurs d'un store voient tous les clients de ce store.
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Super admin voit tout
        if user.is_superuser:
            return queryset
        
        # Vérifier le scope d'accès du rôle
        if hasattr(user, 'role') and user.role:
            # Manager avec accès à tous les clients
            if user.role.access_scope == 'all':
                return queryset
            
            # Utilisateurs assignés à des stores OU avec accès 'own'
            # Tous voient les clients du store (pas seulement ceux qu'ils ont créés)
            elif user.role.access_scope in ['assigned', 'own']:
                assigned_stores = user.assigned_stores.all()
                if assigned_stores.exists():
                    # Importer ici pour éviter les imports circulaires
                    from apps.sales.models import Sale
                    
                    # TOUS les clients qui ont des ventes dans les stores assignés
                    # Peu importe qui a créé le client ou la vente
                    return queryset.filter(
                        sales__store__in=assigned_stores,
                        sales__customer__isnull=False
                    ).distinct()
                else:
                    # Si pas de store assigné, ne voir que ses propres clients
                    return queryset.filter(created_by=user)
        
        # Par défaut, filtrer par créateur (sécurité)
        return queryset.filter(created_by=user)
    
    def perform_create(self, serializer):
        """Enregistrer le créateur du client."""
        # Vérifier la permission
        user = self.request.user
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if not user.role.can_manage_customers:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("Vous n'avez pas la permission de créer des clients.")
        
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Vérifier la permission avant la mise à jour."""
        user = self.request.user
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if not user.role.can_manage_customers:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("Vous n'avez pas la permission de modifier des clients.")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Soft delete: désactiver au lieu de supprimer."""
        # Vérifier la permission
        user = self.request.user
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if not user.role.can_manage_customers:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("Vous n'avez pas la permission de supprimer des clients.")
        
        instance.is_active = False
        instance.save()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CustomerListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CustomerCreateUpdateSerializer
        return CustomerDetailSerializer
    
    
    @extend_schema(summary="Exporter les clients en Excel", tags=["Customers"])
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export customers to Excel."""
        # Use filtered queryset
        customers = self.filter_queryset(self.get_queryset())
        
        wb, ws = ExcelExporter.create_workbook("Clients")
        
        columns = [
            'Code Client', 'Nom', 'Email', 'Téléphone', 'Mobile',
            'Ville', 'Pays', 'Conditions Paiement', 'Limite Crédit', 
            'Solde', 'Actif', 'Date Création'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, customer in enumerate(customers, 2):
            ws.cell(row=row_num, column=1, value=customer.customer_code)
            ws.cell(row=row_num, column=2, value=customer.name)
            ws.cell(row=row_num, column=3, value=customer.email)
            ws.cell(row=row_num, column=4, value=customer.phone)
            ws.cell(row=row_num, column=5, value=customer.mobile)
            ws.cell(row=row_num, column=6, value=customer.city)
            ws.cell(row=row_num, column=7, value=customer.country)
            ws.cell(row=row_num, column=8, value=customer.get_payment_term_display())
            ws.cell(row=row_num, column=9, value=float(customer.credit_limit))
            ws.cell(row=row_num, column=10, value=float(customer.get_balance()))
            ws.cell(row=row_num, column=11, value='Oui' if customer.is_active else 'Non')
            ws.cell(row=row_num, column=12, value=customer.created_at.strftime('%d/%m/%Y'))
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"clients_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)


    @extend_schema(summary="Importer des clients depuis Excel", tags=["Customers"])
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_excel(self, request):
        """Import customers from Excel file."""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
    
        try:
            df = pd.read_excel(file)
            
            # Required columns
            required_columns = ['Nom']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return Response(
                    {'error': f'Colonnes manquantes: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            created_count = 0
            updated_count = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    name = str(row.get('Nom', '')).strip()
                    if not name:
                        errors.append(f"Ligne {index + 2}: Nom obligatoire")
                        continue
                    
                    email = str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else ''
                    phone = str(row.get('Téléphone', '')).strip() if pd.notna(row.get('Téléphone')) else ''
                    customer_code = str(row.get('Code Client', '')).strip() if pd.notna(row.get('Code Client')) else ''

                    # Prepare customer data
                    customer_data = {
                        'name': name,
                        'email': email,
                        'phone': phone,
                        'mobile': str(row.get('Mobile', '')).strip() if pd.notna(row.get('Mobile')) else '',
                        'address': str(row.get('Adresse', '')).strip() if pd.notna(row.get('Adresse')) else '',
                        'city': str(row.get('Ville', '')).strip() if pd.notna(row.get('Ville')) else '',
                        'postal_code': str(row.get('Code Postal', '')).strip() if pd.notna(row.get('Code Postal')) else '',
                        'country': str(row.get('Pays', 'Cameroun')).strip() if pd.notna(row.get('Pays')) else 'Cameroun',
                        'billing_address': str(row.get('Adresse Facturation', '')).strip() if pd.notna(row.get('Adresse Facturation')) else '',
                        'tax_id': str(row.get('Numéro Fiscal', '')).strip() if pd.notna(row.get('Numéro Fiscal')) else '',
                        'credit_limit': float(row.get('Limite Crédit', 0)) if pd.notna(row.get('Limite Crédit')) else 0,
                        'notes': str(row.get('Notes', '')).strip() if pd.notna(row.get('Notes')) else '',
                    }
                    
                    # Handle payment term
                    payment_term_map = {
                        'Comptant': 'immediate',
                        '15 jours': '15_days',
                        '30 jours': '30_days',
                        '60 jours': '60_days',
                        '90 jours': '90_days',
                    }
                    payment_term_str = str(row.get('Conditions Paiement', 'Comptant')).strip()
                    customer_data['payment_term'] = payment_term_map.get(payment_term_str, 'immediate')

                    # Create or update customer
                    if customer_code and Customer.objects.filter(customer_code=customer_code).exists():
                        # Update existing customer
                        customer = Customer.objects.get(customer_code=customer_code)
                        for key, value in customer_data.items():
                            setattr(customer, key, value)
                        customer.save()
                        updated_count += 1
                    else:
                        # Create new customer
                        if not customer_code:
                            # Auto-generate code
                            count = Customer.objects.count() + created_count + 1
                            customer_code = f"CLI{count:05d}"
                        
                        customer_data['customer_code'] = customer_code
                        Customer.objects.create(**customer_data)
                        created_count += 1

                except Exception as e:
                    errors.append(f"Ligne {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Import terminé',
                'created': created_count,
                'updated': updated_count,
                'errors': errors
            })
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de l\'import: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


    @extend_schema(summary="Récupérer les dettes clients", tags=["Customers"])
    @action(detail=False, methods=['get'])
    def debts(self, request):
        """
        Liste les clients avec solde dû pour le tenant courant.
        GET /api/v1/customers/customers/debts/
        Retourne les clients liés à des factures avec un solde non réglé.
        Les données sont automatiquement filtrées par access_scope (own/assigned/all).
        """
        # Utiliser get_queryset() pour respecter le filtrage par access_scope
        customers = self.get_queryset()
        
        data = []
        for customer in customers:
            balance = customer.get_balance()
            if balance > 0:
                # Calculer total_invoiced et total_paid
                invoices = customer.invoices.all()
                
                total_invoiced = 0
                total_paid = 0
                
                for invoice in invoices:
                    invoice_balance = invoice.total_amount - invoice.paid_amount
                    if invoice_balance > 0:
                        total_invoiced += invoice.total_amount
                        total_paid += invoice.paid_amount
                
                data.append({
                    'id': customer.id,
                    'customer_code': customer.customer_code,
                    'name': customer.name,
                    'email': customer.email,
                    'phone': customer.phone,
                    'total_invoiced': float(total_invoiced),
                    'total_paid': float(total_paid),
                    'balance': float(balance),
                    'user_id': customer.user_id if customer.user else None
                })
        
        # Trier par balance décroissante
        data.sort(key=lambda x: x['balance'], reverse=True)
        return Response(data)
    
    
    @extend_schema(summary="Historique des paiements d'un client", tags=["Customers"])
    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get payment history for a customer."""
        customer = self.get_object()
        
        payments = InvoicePayment.objects.filter(
            invoice__customer=customer
        ).select_related('invoice').order_by('payment_date')
        
        payments_data = []
        for payment in payments:
            payments_data.append({
                'id': payment.id,
                'payment_number': payment.payment_number,
                'invoice_number': payment.invoice.invoice_number,
                'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
                'amount': float(payment.amount),
                'payment_method': payment.payment_method,
                'payment_method_display': payment.get_payment_method_display(),
                'reference': payment.reference,
                'notes': payment.notes,
            })
        
        return Response(payments_data)
    
    
    @extend_schema(summary="Créer un paiement client", tags=["Customers"])
    @action(detail=True, methods=['post'], url_path='create-payment', url_name='create-payment')
    def create_payment(self, request, pk=None):
        """Create a payment for a customer invoice. Can distribute payment across multiple invoices."""
        print(f"=== CREATE_PAYMENT called for customer PK: {pk} ===")
        print(f"Request data: {request.data}")
        customer = self.get_object()
        print(f"Customer found: {customer.name} (ID: {customer.id})")
        
        # Récupérer les données du paiement
        invoice_id = request.data.get('invoice_id')
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'cash')
        payment_date_str = request.data.get('payment_date')
        reference = request.data.get('reference', '')
        notes = request.data.get('notes', '')
        
        # Convertir payment_date si fourni
        if payment_date_str:
            try:
                from datetime import datetime
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                payment_date = timezone.now().date()
        else:
            payment_date = timezone.now().date()
        
        if not amount:
            return Response(
                {'error': 'amount est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier le montant
        try:
            # Convertir en Decimal et arrondir à 2 décimales pour éviter les problèmes de précision
            total_amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        except (ValueError, InvalidOperation):
            return Response(
                {'error': 'Montant invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if total_amount <= 0:
            return Response(
                {'error': 'Le montant doit être supérieur à 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si invoice_id est fourni, payer cette facture en priorité
        # Sinon, récupérer toutes les factures impayées du client
        if invoice_id:
            try:
                invoices = [Invoice.objects.get(id=invoice_id, customer=customer)]
            except Invoice.DoesNotExist:
                return Response(
                    {'error': 'Facture introuvable pour ce client'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Récupérer toutes les factures impayées par date
            # Statuts: draft, sent, overdue (tout sauf paid et cancelled)
            all_invoices = Invoice.objects.filter(
                customer=customer
            ).exclude(
                status__in=['paid', 'cancelled']
            ).order_by('invoice_date')
            
            # Filtrer pour ne garder que celles avec un solde > 0
            invoices = [inv for inv in all_invoices if inv.balance_due > 0]
        
        if not invoices or len(invoices) == 0:
            return Response(
                {'error': 'Aucune facture impayée trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Répartir le paiement sur les factures
        remaining_amount = total_amount
        payments_created = []
        
        for invoice in invoices:
            if remaining_amount <= 0:
                break
            
            # Recalculer le solde restant de la facture
            current_balance = invoice.total_amount - invoice.paid_amount
            
            # Calculer le montant à payer pour cette facture
            amount_for_invoice = min(remaining_amount, current_balance)
            
            if amount_for_invoice <= 0:
                continue
            
            # Créer le paiement
            count = InvoicePayment.objects.filter(invoice=invoice).count() + 1
            payment_number = f"{invoice.invoice_number}-P{count:02d}"
            
            payment = InvoicePayment.objects.create(
                payment_number=payment_number,
                invoice=invoice,
                payment_date=payment_date,
                amount=amount_for_invoice,
                payment_method=payment_method,
                reference=reference,
                notes=notes,
                created_by=request.user
            )
            
            # Le signal post_save se charge de recalculer paid_amount et status
            # On rafraîchit juste l'objet pour avoir les valeurs à jour
            invoice.refresh_from_db()
            
            payments_created.append({
                'id': payment.id,
                'payment_number': payment.payment_number,
                'invoice_number': invoice.invoice_number,
                'amount': float(payment.amount),
                'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
                'balance_before': float(current_balance),
                'balance_after': float(invoice.total_amount - invoice.paid_amount),
            })
            
            remaining_amount -= amount_for_invoice
        
        return Response({
            'success': True,
            'total_amount': float(total_amount),
            'amount_applied': float(total_amount - remaining_amount),
            'remaining_amount': float(remaining_amount),
            'payments': payments_created,
            'message': f'{len(payments_created)} paiement(s) créé(s) avec succès'
        }, status=status.HTTP_201_CREATED)