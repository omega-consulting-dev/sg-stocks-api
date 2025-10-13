from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.loans.models import Loan, LoanPayment, LoanSchedule
from apps.loans.serializers import (
    LoanListSerializer, LoanDetailSerializer, LoanCreateSerializer,
    LoanPaymentSerializer, LoanScheduleSerializer
)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    filterset_fields = ['loan_type', 'status']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LoanListSerializer
        elif self.action == 'create':
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