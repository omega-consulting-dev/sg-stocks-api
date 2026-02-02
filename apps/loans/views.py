from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from decimal import Decimal
from core.utils.export_utils import ExcelExporter
from apps.loans.models import Loan, LoanPayment, LoanSchedule
from apps.loans.serializers import (
    LoanListSerializer, LoanDetailSerializer, LoanCreateSerializer,
    LoanPaymentSerializer, LoanScheduleSerializer
)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    permission_classes = [IsAuthenticated]
    module_name = 'loans'
    filterset_fields = ['loan_type', 'status']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrage par rôle
        if user.is_superuser:
            pass
        elif hasattr(user, 'role') and user.role:
            if user.role.access_scope == 'all':
                pass
            elif user.role.access_scope == 'assigned':
                # Voir les emprunts des stores assignés
                if hasattr(user, 'assigned_stores') and user.assigned_stores.exists():
                    queryset = queryset.filter(store__in=user.assigned_stores.all())
                else:
                    queryset = queryset.filter(created_by=user)
            elif user.role.access_scope == 'own':
                queryset = queryset.filter(created_by=user)
        else:
            queryset = queryset.filter(created_by=user)
        
        # Filtrage par date
        start_date_gte = self.request.query_params.get('start_date__gte')
        start_date_lte = self.request.query_params.get('start_date__lte')
        
        if start_date_gte:
            queryset = queryset.filter(start_date__gte=start_date_gte)
        if start_date_lte:
            queryset = queryset.filter(start_date__lte=start_date_lte)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LoanListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return LoanCreateSerializer
        return LoanDetailSerializer
    
    def perform_create(self, serializer):
        """Définir automatiquement created_by lors de la création"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='export_excel')
    def export_excel(self, request):
        """Export loans to Excel."""
        loans = self.get_queryset()
        
        # Appliquer les filtres si présents
        loan_type = request.query_params.get('loan_type')
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('start_date__gte')
        date_to = request.query_params.get('start_date__lte')
        
        if loan_type:
            loans = loans.filter(loan_type=loan_type)
        if status_filter:
            loans = loans.filter(status=status_filter)
        if date_from:
            loans = loans.filter(start_date__gte=date_from)
        if date_to:
            loans = loans.filter(start_date__lte=date_to)
        
        wb, ws = ExcelExporter.create_workbook("Emprunts")
        
        columns = [
            'N° Emprunt', 'Type', 'Prêteur', 'Date Début', 'Date Fin',
            'Montant Principal', 'Taux (%)', 'Durée (mois)', 
            'Montant Total', 'Montant Payé', 'Solde Restant', 'Statut'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, loan in enumerate(loans, 2):
            ws.cell(row=row_num, column=1, value=loan.loan_number)
            ws.cell(row=row_num, column=2, value=loan.get_loan_type_display())
            ws.cell(row=row_num, column=3, value=loan.lender_name)
            ws.cell(row=row_num, column=4, value=loan.start_date.strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=5, value=loan.end_date.strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=6, value=float(loan.principal_amount))
            ws.cell(row=row_num, column=7, value=float(loan.interest_rate))
            ws.cell(row=row_num, column=8, value=loan.duration_months)
            ws.cell(row=row_num, column=9, value=float(loan.total_amount))
            ws.cell(row=row_num, column=10, value=float(loan.paid_amount))
            ws.cell(row=row_num, column=11, value=float(loan.balance_due))
            ws.cell(row=row_num, column=12, value=loan.get_status_display())
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"emprunts_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)
    
    @action(detail=True, methods=['post'])
    def make_payment(self, request, pk=None):
        """Record a loan payment."""
        loan = self.get_object()
        amount = Decimal(str(request.data.get('amount')))
        payment_method = request.data.get('payment_method')
        
        # Utiliser le store de l'emprunt
        store = loan.store
        
        if not store:
            return Response(
                {'error': 'L\'emprunt n\'a pas de point de vente associé.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier le solde disponible selon le mode de paiement
        if payment_method == 'cash':
            # Vérifier le solde de la caisse
            from apps.cashbox.utils import get_cashbox_real_balance
            
            available_balance = get_cashbox_real_balance(store_id=store.id)
            
            if amount > available_balance:
                return Response(
                    {
                        'error': f'Solde en caisse insuffisant. Solde disponible: {available_balance:,.2f} XAF, Montant demandé: {amount:,.2f} XAF'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        elif payment_method == 'bank_transfer':
            # Vérifier le solde bancaire
            from apps.cashbox.utils import get_bank_balance
            
            bank_balance = get_bank_balance(store_id=store.id)
            
            if amount > bank_balance:
                return Response(
                    {
                        'error': f'Solde bancaire insuffisant. Solde disponible: {bank_balance:,.2f} XAF, Montant demandé: {amount:,.2f} XAF'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        elif payment_method == 'mobile_money':
            # Vérifier le solde Mobile Money
            from apps.cashbox.utils import get_mobile_money_balance
            
            mobile_money_balance = get_mobile_money_balance(store_id=store.id)
            
            if amount > mobile_money_balance:
                return Response(
                    {
                        'error': f'Solde Mobile Money insuffisant. Solde disponible: {mobile_money_balance:,.2f} XAF, Montant demandé: {amount:,.2f} XAF'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create payment
        count = LoanPayment.objects.filter(loan=loan).count() + 1
        payment = LoanPayment.objects.create(
            payment_number=f"{loan.loan_number}-PAY{count:03d}",
            loan=loan,
            payment_date=timezone.now().date(),
            amount=amount,
            payment_method=payment_method,
            created_by=request.user
        )
        
        # Gérer les mouvements de caisse selon le mode de paiement
        if payment_method == 'cash':
            # Paiement en espèces: créer un mouvement de sortie de caisse
            from apps.cashbox.models import Cashbox, CashboxSession, CashMovement
            
            cashbox, _ = Cashbox.objects.get_or_create(
                store=store,
                is_active=True,
                defaults={
                    'name': f'Caisse {store.name}',
                    'code': f'CASH-{store.code}',
                    'created_by': request.user
                }
            )
            
            # Récupérer ou créer une session ouverte
            cashbox_session, _ = CashboxSession.objects.get_or_create(
                cashbox=cashbox,
                status='open',
                defaults={
                    'cashier': request.user,
                    'opening_date': timezone.now(),
                    'opening_balance': 0,
                    'created_by': request.user
                }
            )
            
            # Créer le mouvement de sortie de caisse
            last_movement = CashMovement.objects.order_by('-id').first()
            if last_movement and last_movement.movement_number:
                try:
                    import re
                    match = re.search(r'\d+', last_movement.movement_number)
                    if match:
                        last_number = int(match.group())
                        movement_count = last_number + 1
                    else:
                        movement_count = CashMovement.objects.count() + 1
                except (ValueError, AttributeError):
                    movement_count = CashMovement.objects.count() + 1
            else:
                movement_count = 1
            
            CashMovement.objects.create(
                movement_number=f'LOAN-{movement_count:05d}',
                cashbox_session=cashbox_session,
                movement_type='out',  # Argent sort de la caisse
                category='loan_payment',
                amount=amount,
                payment_method='cash',
                reference=payment.payment_number,
                description=f'Remboursement emprunt {loan.loan_number} en espèces',
                created_by=request.user
            )
            
            # Mettre à jour le solde de la caisse (diminuer)
            cashbox.current_balance -= amount
            cashbox.save()
        
        # Note: Pour les paiements par virement bancaire et Mobile Money, on ne crée PAS de CashMovement
        # car l'argent sort directement de la banque/Mobile Money sans passer par la caisse physique.
        # Le solde Mobile Money est calculé automatiquement via les LoanPayment dans get_mobile_money_balance()
        
        # Update loan paid amount
        loan.paid_amount += amount
        if loan.is_fully_paid:
            loan.status = 'paid'
        loan.save()
        
        # Update schedule
        remaining = amount
        for schedule in loan.schedule.filter(status__in=['pending', 'partial']).order_by('due_date'):
            if remaining <= 0:
                break
            
            payment_for_installment = min(remaining, schedule.balance_due)
            schedule.paid_amount += payment_for_installment
            
            if schedule.paid_amount >= schedule.total_amount:
                schedule.status = 'paid'
                schedule.payment_date = timezone.now().date()
            else:
                schedule.status = 'partial'
            
            schedule.save()
            remaining -= payment_for_installment
        
        serializer = LoanPaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get payment history for a loan."""
        loan = self.get_object()
        payments = LoanPayment.objects.filter(loan=loan).order_by('-payment_date')
        serializer = LoanPaymentSerializer(payments, many=True)
        return Response(serializer.data)


class LoanPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoanPayment.objects.select_related('loan')
    serializer_class = LoanPaymentSerializer
    filterset_fields = ['loan']
    permission_classes = [IsAuthenticated]
    module_name = 'loans'


class LoanExportExcelView(APIView):
    """Vue pour exporter les emprunts en Excel."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Export loans to Excel."""
        loans = Loan.objects.all()
        
        # Appliquer les filtres si présents
        loan_type = request.query_params.get('loan_type')
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('start_date__gte')
        date_to = request.query_params.get('start_date__lte')
        
        if loan_type:
            loans = loans.filter(loan_type=loan_type)
        if status_filter:
            loans = loans.filter(status=status_filter)
        if date_from:
            loans = loans.filter(start_date__gte=date_from)
        if date_to:
            loans = loans.filter(start_date__lte=date_to)
        
        wb, ws = ExcelExporter.create_workbook("Emprunts")
        
        columns = [
            'N° Emprunt', 'Type', 'Prêteur', 'Date Début', 'Date Fin',
            'Montant Principal', 'Taux (%)', 'Durée (mois)', 
            'Montant Total', 'Montant Payé', 'Solde Restant', 'Statut'
        ]
        ExcelExporter.style_header(ws, columns)
        
        for row_num, loan in enumerate(loans, 2):
            ws.cell(row=row_num, column=1, value=loan.loan_number)
            ws.cell(row=row_num, column=2, value=loan.get_loan_type_display())
            ws.cell(row=row_num, column=3, value=loan.lender_name)
            ws.cell(row=row_num, column=4, value=loan.start_date.strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=5, value=loan.end_date.strftime('%d/%m/%Y'))
            ws.cell(row=row_num, column=6, value=float(loan.principal_amount))
            ws.cell(row=row_num, column=7, value=float(loan.interest_rate))
            ws.cell(row=row_num, column=8, value=loan.duration_months)
            ws.cell(row=row_num, column=9, value=float(loan.total_amount))
            ws.cell(row=row_num, column=10, value=float(loan.paid_amount))
            ws.cell(row=row_num, column=11, value=float(loan.balance_due))
            ws.cell(row=row_num, column=12, value=loan.get_status_display())
        
        ExcelExporter.auto_adjust_columns(ws)
        
        filename = f"emprunts_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelExporter.generate_response(wb, filename)