from rest_framework import serializers
from apps.expenses.models import Expense, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'code', 'description', 'is_active', 'created_at']


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'expense_number', 'category', 'category_name', 'store',
            'expense_date', 'description', 'amount', 'beneficiary',
            'payment_method', 'payment_reference', 'payment_date',
            'status', 'status_display', 'is_paid', 'approved_by',
            'approval_date', 'receipt', 'notes', 'created_at'
        ]