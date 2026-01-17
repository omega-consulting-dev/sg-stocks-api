from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
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
        
        if user.is_superuser:
            return queryset
        
        if hasattr(user, 'role') and user.role:
            if user.role.access_scope == 'all':
                return queryset
            elif user.role.access_scope == 'own':
                return queryset.filter(created_by=user)
        
        return queryset.filter(created_by=user)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LoanListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return LoanCreateSerializer
        return LoanDetailSerializer
    
    @action(detail=True, methods=['post'])
    def make_payment(self, request, pk=None):
        """Record a loan payment."""
        loan = self.get_object()
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method')
        
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