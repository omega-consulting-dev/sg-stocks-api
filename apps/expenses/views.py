from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.expenses.models import Expense, ExpenseCategory
from apps.expenses.serializers import ExpenseSerializer, ExpenseCategorySerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.filter(is_active=True)
    serializer_class = ExpenseCategorySerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related('category', 'store')
    serializer_class = ExpenseSerializer
    filterset_fields = ['category', 'store', 'status', 'expense_date']
    
    def perform_create(self, serializer):
        count = Expense.objects.count() + 1
        serializer.save(
            expense_number=f"EXP{count:08d}",
            created_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an expense."""
        expense = self.get_object()
        
        if expense.status != 'pending':
            return Response(
                {'error': 'Seules les dépenses en attente peuvent être approuvées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'approved'
        expense.approved_by = request.user
        expense.approval_date = timezone.now()
        expense.save()
        
        serializer = self.get_serializer(expense)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an expense."""
        expense = self.get_object()
        
        if expense.status != 'pending':
            return Response(
                {'error': 'Seules les dépenses en attente peuvent être rejetées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'rejected'
        expense.save()
        
        serializer = self.get_serializer(expense)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Mark expense as paid."""
        expense = self.get_object()
        
        if expense.status != 'approved':
            return Response(
                {'error': 'Seules les dépenses approuvées peuvent être payées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'paid'
        expense.payment_date = timezone.now().date()
        expense.payment_method = request.data.get('payment_method')
        expense.payment_reference = request.data.get('payment_reference', '')
        expense.save()
        
        serializer = self.get_serializer(expense)
        return Response(serializer.data)