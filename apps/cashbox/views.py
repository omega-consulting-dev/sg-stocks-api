from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q, Sum, F
from apps.cashbox.models import Cashbox, CashboxSession, CashMovement
from apps.cashbox.serializers import (
    CashboxSerializer, 
    CashboxSessionSerializer, 
    CashMovementSerializer,
    EncaissementSerializer
)
from apps.invoicing.models import InvoicePayment
from apps.sales.models import Sale
from apps.expenses.models import Expense
from apps.suppliers.models import SupplierPayment
from apps.loans.models import LoanPayment
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter


class CashboxViewSet(viewsets.ModelViewSet):
    queryset = Cashbox.objects.select_related('store')
    serializer_class = CashboxSerializer
    filterset_fields = ['store', 'is_active']


class CashboxSessionViewSet(viewsets.ModelViewSet):
    queryset = CashboxSession.objects.select_related('cashbox', 'cashier')
    serializer_class = CashboxSessionSerializer
    filterset_fields = ['cashbox', 'cashier', 'status']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        if hasattr(user, 'role') and user.role:
            if user.role.access_scope == 'all':
                return queryset
            elif user.role.access_scope == 'assigned':
                return queryset.filter(cashbox__store__in=user.assigned_stores.all())
            elif user.role.access_scope == 'own':
                return queryset.filter(cashier=user)
        
        return queryset.filter(cashier=user)
    
    @action(detail=False, methods=['post'])
    def open_session(self, request):
        """Open a new cashbox session."""
        cashbox_id = request.data.get('cashbox')
        opening_balance = request.data.get('opening_balance', 0)
        
        # Check if there's already an open session
        if CashboxSession.objects.filter(cashbox_id=cashbox_id, status='open').exists():
            return Response(
                {'error': 'Une session est déjà ouverte pour cette caisse.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = CashboxSession.objects.create(
            cashbox_id=cashbox_id,
            cashier=request.user,
            opening_date=timezone.now(),
            opening_balance=opening_balance,
            status='open',
            created_by=request.user
        )
        
        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def close_session(self, request, pk=None):
        """Close a cashbox session."""
        session = self.get_object()
        
        if session.status != 'open':
            return Response(
                {'error': 'Cette session est déjà fermée.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        actual_balance = request.data.get('actual_closing_balance')
        closing_notes = request.data.get('closing_notes', '')
        
        # Calculate expected balance
        from django.db.models import Sum, Case, When, F
        movements = CashMovement.objects.filter(cashbox_session=session)
        total_in = movements.filter(movement_type='in').aggregate(total=Sum('amount'))['total'] or 0
        total_out = movements.filter(movement_type='out').aggregate(total=Sum('amount'))['total'] or 0
        
        session.expected_closing_balance = session.opening_balance + total_in - total_out
        session.actual_closing_balance = actual_balance
        session.closing_date = timezone.now()
        session.closing_notes = closing_notes
        session.status = 'closed'
        session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)


class CashMovementViewSet(viewsets.ModelViewSet):
    queryset = CashMovement.objects.select_related('cashbox_session', 'sale')
    serializer_class = CashMovementSerializer
    filterset_fields = ['cashbox_session', 'movement_type', 'category', 'payment_method']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        if hasattr(user, 'role') and user.role:
            if user.role.access_scope == 'all':
                return queryset
            elif user.role.access_scope == 'assigned':
                return queryset.filter(cashbox_session__cashbox__store__in=user.assigned_stores.all())
            elif user.role.access_scope == 'own':
                return queryset.filter(created_by=user)
        
        return queryset.filter(created_by=user)
    
    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Received data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        # Generate movement number
        count = CashMovement.objects.count() + 1
        movement = serializer.save(
            movement_number=f"MVT{count:08d}",
            created_by=self.request.user
        )


class EncaissementsListView(APIView):
    """
    Vue pour lister tous les encaissements (paiements de factures + ventes payées)
    """
    
    def get(self, request):
        user = request.user
        
        # Récupérer les paramètres de filtre
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        store_id = request.query_params.get('store')
        
        # Validation des dates
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                if start > end:
                    return Response(
                        {'error': 'La date de début ne peut pas être supérieure à la date de fin'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        encaissements = []
        
        # 1. Récupérer les paiements de factures
        invoice_payments = InvoicePayment.objects.select_related('invoice', 'invoice__customer', 'invoice__store').all()
        
        # Filtrage selon le rôle
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if user.role.access_scope == 'all':
                    pass  # Voir tout
                elif user.role.access_scope == 'assigned':
                    invoice_payments = invoice_payments.filter(invoice__store__in=user.assigned_stores.all())
                elif user.role.access_scope == 'own':
                    invoice_payments = invoice_payments.filter(invoice__created_by=user)
            else:
                invoice_payments = invoice_payments.filter(invoice__created_by=user)
        
        if start_date:
            invoice_payments = invoice_payments.filter(payment_date__gte=start_date)
        if end_date:
            invoice_payments = invoice_payments.filter(payment_date__lte=end_date)
        if store_id:
            invoice_payments = invoice_payments.filter(invoice__store_id=store_id)
        
        for payment in invoice_payments:
            encaissements.append({
                'id': f'INV-{payment.id}',
                'code': payment.payment_number,
                'type': 'invoice_payment',
                'date': payment.payment_date,
                'reference_facture': payment.invoice.invoice_number,
                'montant': float(payment.amount),
                'mode_paiement': payment.get_payment_method_display(),
                'client': payment.invoice.customer.name if payment.invoice.customer else '',
                'created_at': payment.created_at,
            })
        
        # 2. Récupérer les ventes avec paiement
        sales = Sale.objects.select_related('customer', 'store').filter(paid_amount__gt=0)
        
        # Filtrage selon le rôle
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if user.role.access_scope == 'all':
                    pass  # Voir tout
                elif user.role.access_scope == 'assigned':
                    sales = sales.filter(store__in=user.assigned_stores.all())
                elif user.role.access_scope == 'own':
                    sales = sales.filter(created_by=user)
            else:
                sales = sales.filter(created_by=user)
        
        if start_date:
            sales = sales.filter(sale_date__gte=start_date)
        if end_date:
            sales = sales.filter(sale_date__lte=end_date)
        
        for sale in sales:
            encaissements.append({
                'id': f'SALE-{sale.id}',
                'code': sale.sale_number,
                'type': 'sale',
                'date': sale.sale_date,
                'reference_facture': sale.sale_number,
                'montant': float(sale.paid_amount),
                'mode_paiement': 'Vente directe',
                'client': sale.customer.name if sale.customer else 'Client anonyme',
                'created_at': sale.created_at,
            })
        
        # Trier par date décroissante
        encaissements.sort(key=lambda x: x['date'], reverse=True)
        
        # Paginer les résultats
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated = encaissements[start_idx:end_idx]
        
        return Response({
            'count': len(encaissements),
            'next': None if end_idx >= len(encaissements) else f'?page={page + 1}',
            'previous': None if page == 1 else f'?page={page - 1}',
            'results': paginated
        })


class EncaissementsExportView(APIView):
    """
    Vue pour exporter les encaissements en Excel
    """
    
    def get(self, request):
        user = request.user
        
        # Récupérer les paramètres de filtre
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        store_id = request.query_params.get('store')
        
        # Validation des dates
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                if start > end:
                    return Response(
                        {'error': 'La date de début ne peut pas être supérieure à la date de fin'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        encaissements = []
        
        # 1. Récupérer les paiements de factures
        invoice_payments = InvoicePayment.objects.select_related('invoice', 'invoice__customer', 'invoice__store').all()
        
        # Filtrage selon le rôle
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if user.role.access_scope == 'all':
                    pass
                elif user.role.access_scope == 'assigned':
                    invoice_payments = invoice_payments.filter(invoice__store__in=user.assigned_stores.all())
                elif user.role.access_scope == 'own':
                    invoice_payments = invoice_payments.filter(invoice__created_by=user)
            else:
                invoice_payments = invoice_payments.filter(invoice__created_by=user)
        
        if start_date:
            invoice_payments = invoice_payments.filter(payment_date__gte=start_date)
        if end_date:
            invoice_payments = invoice_payments.filter(payment_date__lte=end_date)
        if store_id:
            invoice_payments = invoice_payments.filter(invoice__store_id=store_id)
        
        for payment in invoice_payments:
            encaissements.append({
                'code': payment.payment_number,
                'type': 'Paiement Facture',
                'date': payment.payment_date,
                'reference_facture': payment.invoice.invoice_number,
                'montant': float(payment.amount),
                'mode_paiement': payment.get_payment_method_display(),
                'client': payment.invoice.customer.name if payment.invoice.customer else '',
            })
        
        # 2. Récupérer les ventes avec paiement
        sales = Sale.objects.select_related('customer', 'store').filter(paid_amount__gt=0)
        
        # Filtrage selon le rôle
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if user.role.access_scope == 'all':
                    pass
                elif user.role.access_scope == 'assigned':
                    sales = sales.filter(store__in=user.assigned_stores.all())
                elif user.role.access_scope == 'own':
                    sales = sales.filter(created_by=user)
            else:
                sales = sales.filter(created_by=user)
        
        if start_date:
            sales = sales.filter(sale_date__gte=start_date)
        if end_date:
            sales = sales.filter(sale_date__lte=end_date)
        if store_id:
            sales = sales.filter(store_id=store_id)
        
        for sale in sales:
            encaissements.append({
                'code': sale.sale_number,
                'type': 'Vente',
                'date': sale.sale_date,
                'reference_facture': sale.sale_number,
                'montant': float(sale.paid_amount),
                'mode_paiement': 'Vente directe',
                'client': sale.customer.name if sale.customer else 'Client anonyme',
            })
        
        # Trier par date
        encaissements.sort(key=lambda x: x['date'])
        
        # Créer le fichier Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Encaissements"
        
        # Style pour l'en-tête
        header_fill = PatternFill(start_color="5932EA", end_color="5932EA", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # En-têtes
        headers = ['Code', 'Type', 'Date', 'Référence', 'Montant (FCFA)', 'Mode de paiement', 'Client']
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
        
        # Données
        for row_num, enc in enumerate(encaissements, 2):
            ws.cell(row=row_num, column=1, value=enc['code'])
            ws.cell(row=row_num, column=2, value=enc['type'])
            ws.cell(row=row_num, column=3, value=enc['date'].strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=4, value=enc['reference_facture'])
            ws.cell(row=row_num, column=5, value=enc['montant'])
            ws.cell(row=row_num, column=6, value=enc['mode_paiement'])
            ws.cell(row=row_num, column=7, value=enc['client'])
        
        # Ajouter une ligne de total
        total_row = len(encaissements) + 2
        ws.cell(row=total_row, column=4, value="TOTAL")
        ws.cell(row=total_row, column=4).font = Font(bold=True)
        total_montant = sum(enc['montant'] for enc in encaissements)
        ws.cell(row=total_row, column=5, value=total_montant)
        ws.cell(row=total_row, column=5).font = Font(bold=True)
        
        # Ajuster la largeur des colonnes
        for col in range(1, 8):
            ws.column_dimensions[get_column_letter(col)].width = 20
        
        # Préparer la réponse
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Nom du fichier avec période si applicable
        filename = 'encaissements'
        if start_date and end_date:
            filename += f'_{start_date}_au_{end_date}'
        elif start_date:
            filename += f'_depuis_{start_date}'
        elif end_date:
            filename += f'_jusquau_{end_date}'
        filename += '.xlsx'
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        
        return response


class CaisseSoldeView(APIView):
    """
    Vue pour calculer le solde actuel de la caisse
    Prend en compte : encaissements - dépenses - paiements fournisseurs - remboursements emprunts
    """
    
    def get(self, request):
        user = request.user
        
        # Récupérer le paramètre store
        store_id = request.query_params.get('store')
        
        # Total des encaissements (entrées d'argent)
        # 1. Paiements de factures
        invoice_payments_qs = InvoicePayment.objects.all()
        
        # Filtrage par utilisateur - ALIGNÉ AVEC LE DASHBOARD
        if user.is_superuser or (hasattr(user, 'role') and user.role and user.role.access_scope == 'all'):
            # Admin voit tous les paiements
            pass
        else:
            # Utilisateur normal voit uniquement les paiements des factures qu'il a créées
            invoice_payments_qs = invoice_payments_qs.filter(invoice__created_by=user)
        
        if store_id:
            invoice_payments_qs = invoice_payments_qs.filter(invoice__store_id=store_id)
        total_invoice_payments = invoice_payments_qs.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # 2. Ventes payées (créées par l'utilisateur)
        sales_qs = Sale.objects.all()
        
        # Filtrage par utilisateur - ALIGNÉ AVEC LE DASHBOARD
        if user.is_superuser or (hasattr(user, 'role') and user.role and user.role.access_scope == 'all'):
            # Admin voit toutes les ventes
            pass
        else:
            # Utilisateur normal voit uniquement les ventes qu'il a créées
            sales_qs = sales_qs.filter(created_by=user)
        
        if store_id:
            sales_qs = sales_qs.filter(store_id=store_id)
        total_sales = sales_qs.aggregate(
            total=Sum('paid_amount')
        )['total'] or 0
        
        total_encaissements = total_invoice_payments + total_sales
        
        # Total des sorties d'argent
        # 1. Dépenses
        expenses_qs = Expense.objects.all()
        
        # Filtrage par utilisateur - ALIGNÉ AVEC LE DASHBOARD
        if user.is_superuser or (hasattr(user, 'role') and user.role and user.role.access_scope == 'all'):
            # Admin voit toutes les dépenses
            pass
        else:
            # Utilisateur normal voit uniquement les dépenses qu'il a créées
            expenses_qs = expenses_qs.filter(created_by=user)
        
        if store_id:
            expenses_qs = expenses_qs.filter(store_id=store_id)
        total_expenses = expenses_qs.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # 2. Paiements fournisseurs
        supplier_payments_qs = SupplierPayment.objects.all()
        
        # Filtrage par utilisateur - ALIGNÉ AVEC LE DASHBOARD
        if user.is_superuser or (hasattr(user, 'role') and user.role and user.role.access_scope == 'all'):
            # Admin voit tous les paiements
            pass
        else:
            # Utilisateur normal voit uniquement les paiements qu'il a créés
            supplier_payments_qs = supplier_payments_qs.filter(created_by=user)
        
        # Note: SupplierPayment n'a pas de champ store
        total_supplier_payments = supplier_payments_qs.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # 3. Remboursements d'emprunts
        loan_payments_qs = LoanPayment.objects.all()
        
        # Filtrage par utilisateur - ALIGNÉ AVEC LE DASHBOARD
        if user.is_superuser or (hasattr(user, 'role') and user.role and user.role.access_scope == 'all'):
            # Admin voit tous les remboursements
            pass
        else:
            # Utilisateur normal voit uniquement les remboursements qu'il a créés
            loan_payments_qs = loan_payments_qs.filter(created_by=user)
        
        if store_id:
            loan_payments_qs = loan_payments_qs.filter(loan__store_id=store_id)
        total_loan_payments = loan_payments_qs.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # 4. Décaissements (mouvements de caisse sortants)
        cash_movements_out_qs = CashMovement.objects.filter(movement_type='out')
        
        # Filtrage par utilisateur - ALIGNÉ AVEC LE DASHBOARD
        if user.is_superuser or (hasattr(user, 'role') and user.role and user.role.access_scope == 'all'):
            # Admin voit tous les mouvements
            pass
        else:
            # Utilisateur normal voit uniquement les mouvements qu'il a créés
            cash_movements_out_qs = cash_movements_out_qs.filter(created_by=user)
        
        if store_id:
            cash_movements_out_qs = cash_movements_out_qs.filter(cashbox_session__cashbox__store_id=store_id)
        total_cash_movements_out = cash_movements_out_qs.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_sorties = total_expenses + total_supplier_payments + total_loan_payments + total_cash_movements_out
        
        # Solde de caisse = Encaissements - Sorties
        solde_caisse = total_encaissements - total_sorties
        
        return Response({
            'solde_actuel': float(solde_caisse),
            'total_encaissements': float(total_encaissements),
            'total_sorties': float(total_sorties),
            'details': {
                'paiements_factures': float(total_invoice_payments),
                'ventes': float(total_sales),
                'depenses': float(total_expenses),
                'paiements_fournisseurs': float(total_supplier_payments),
                'remboursements_emprunts': float(total_loan_payments),
                'decaissements': float(total_cash_movements_out),
            }
        })


class DecaissementsListView(APIView):
    """
    Vue pour lister tous les décaissements (approvisionnements bancaires)
    """
    
    def get(self, request):
        user = request.user
        
        # Récupérer les paramètres de filtre
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        store_id = request.query_params.get('store')
        
        # Validation des dates
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                if start > end:
                    return Response(
                        {'error': 'La date de début ne peut pas être supérieure à la date de fin'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        decaissements = []
        
        # Récupérer tous les mouvements de caisse de type "out" avec catégorie "bank_deposit"
        cash_movements = CashMovement.objects.filter(
            movement_type='out',
            category='bank_deposit'
        ).select_related('cashbox_session', 'cashbox_session__cashbox', 'cashbox_session__cashbox__store').order_by('created_at')
        
        # Filtrage selon le rôle
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if user.role.access_scope == 'all':
                    pass  # Voir tout
                elif user.role.access_scope == 'assigned':
                    cash_movements = cash_movements.filter(cashbox_session__cashbox__store__in=user.assigned_stores.all())
                elif user.role.access_scope == 'own':
                    cash_movements = cash_movements.filter(created_by=user)
            else:
                cash_movements = cash_movements.filter(created_by=user)
        
        if start_date:
            cash_movements = cash_movements.filter(created_at__date__gte=start_date)
        if end_date:
            cash_movements = cash_movements.filter(created_at__date__lte=end_date)
        if store_id:
            cash_movements = cash_movements.filter(cashbox_session__cashbox__store_id=store_id)
        
        for movement in cash_movements:
            decaissements.append({
                'id': f'DEC-{movement.id}',
                'code': movement.movement_number,
                'type': 'Approvisionnement Bancaire',
                'date': movement.created_at.date(),
                'reference': movement.reference or movement.movement_number,
                'montant': float(movement.amount),
                'mode_paiement': movement.get_payment_method_display(),
                'description': movement.description,
                'created_at': movement.created_at,
            })
        
        # Trier par date décroissante
        decaissements.sort(key=lambda x: x['date'], reverse=True)
        
        # Paginer les résultats
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated = decaissements[start_idx:end_idx]
        
        return Response({
            'count': len(decaissements),
            'next': None if end_idx >= len(decaissements) else f'?page={page + 1}',
            'previous': None if page == 1 else f'?page={page - 1}',
            'results': paginated
        })


class DecaissementsExportView(APIView):
    """
    Vue pour exporter les décaissements en Excel
    """
    
    def get(self, request):
        user = request.user
        
        # Récupérer les paramètres de filtre
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        store_id = request.query_params.get('store')
        
        # Validation des dates
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                if start > end:
                    return Response(
                        {'error': 'La date de début ne peut pas être supérieure à la date de fin'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        decaissements = []
        
        # Récupérer tous les mouvements de caisse de type "out" avec catégorie "bank_deposit"
        cash_movements = CashMovement.objects.filter(
            movement_type='out',
            category='bank_deposit'
        ).select_related('cashbox_session', 'cashbox_session__cashbox', 'cashbox_session__cashbox__store').order_by('created_at')
        
        # Filtrage selon le rôle
        if not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if user.role.access_scope == 'all':
                    pass
                elif user.role.access_scope == 'assigned':
                    cash_movements = cash_movements.filter(cashbox_session__cashbox__store__in=user.assigned_stores.all())
                elif user.role.access_scope == 'own':
                    cash_movements = cash_movements.filter(created_by=user)
            else:
                cash_movements = cash_movements.filter(created_by=user)
        
        if start_date:
            cash_movements = cash_movements.filter(created_at__date__gte=start_date)
        if end_date:
            cash_movements = cash_movements.filter(created_at__date__lte=end_date)
        if store_id:
            cash_movements = cash_movements.filter(cashbox_session__cashbox__store_id=store_id)
        
        for movement in cash_movements:
            decaissements.append({
                'code': movement.movement_number,
                'type': 'Approvisionnement Bancaire',
                'date': movement.created_at.date(),
                'reference': movement.reference or movement.movement_number,
                'montant': float(movement.amount),
                'mode_paiement': movement.get_payment_method_display(),
                'description': movement.description,
            })
        
        # Créer le fichier Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Décaissements"
        
        # Style pour l'en-tête
        header_fill = PatternFill(start_color="5932EA", end_color="5932EA", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # En-têtes
        headers = ['Code', 'Type', 'Date', 'Référence', 'Montant (FCFA)', 'Mode de paiement', 'Description']
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
        
        # Données
        for row_num, dec in enumerate(decaissements, 2):
            ws.cell(row=row_num, column=1, value=dec['code'])
            ws.cell(row=row_num, column=2, value=dec['type'])
            ws.cell(row=row_num, column=3, value=dec['date'].strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=4, value=dec['reference'])
            ws.cell(row=row_num, column=5, value=dec['montant'])
            ws.cell(row=row_num, column=6, value=dec['mode_paiement'])
            ws.cell(row=row_num, column=7, value=dec['description'])
        
        # Ajouter une ligne de total
        total_row = len(decaissements) + 2
        ws.cell(row=total_row, column=4, value="TOTAL")
        ws.cell(row=total_row, column=4).font = Font(bold=True)
        total_montant = sum(dec['montant'] for dec in decaissements)
        ws.cell(row=total_row, column=5, value=total_montant)
        ws.cell(row=total_row, column=5).font = Font(bold=True)
        
        # Ajuster la largeur des colonnes
        for col in range(1, 8):
            ws.column_dimensions[get_column_letter(col)].width = 20
        
        # Préparer la réponse
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Nom du fichier avec période si applicable
        filename = 'decaissements'
        if start_date and end_date:
            filename += f'_{start_date}_au_{end_date}'
        elif start_date:
            filename += f'_depuis_{start_date}'
        elif end_date:
            filename += f'_jusquau_{end_date}'
        filename += '.xlsx'
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        
        return response


class StoreListView(APIView):
    """
    Vue simple pour récupérer la liste des stores actifs
    """
    
    def get(self, request):
        from apps.inventory.models import Store
        
        stores = Store.objects.filter(is_active=True).values('id', 'name', 'code', 'store_type')
        return Response(list(stores))
