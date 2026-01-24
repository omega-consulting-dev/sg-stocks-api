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
    payment_method = serializers.ChoiceField(
        choices=Expense.PAYMENT_METHOD_CHOICES,
        allow_null=True,
        required=False
    )
    
    def get_fields(self):
        """Override to dynamically set store queryset for multi-tenant"""
        fields = super().get_fields()
        request = self.context.get('request')
        if request and hasattr(request, 'tenant'):
            from apps.inventory.models import Store
            fields['store'] = serializers.PrimaryKeyRelatedField(
                queryset=Store.objects.all(),
                allow_null=True,
                required=False
            )
        else:
            fields['store'] = serializers.PrimaryKeyRelatedField(
                queryset=None,
                allow_null=True,
                required=False,
                read_only=True
            )
        return fields
    
    def update(self, instance, validated_data):
        """Override update to handle null values properly"""
        request = self.context.get('request')
        if request:
            # Handle store field - treat empty string as null
            if 'store' in request.data:
                store_value = request.data.get('store')
                if store_value == '' or store_value is None:
                    instance.store = None
                else:
                    instance.store = validated_data.get('store')
            
            # Handle payment_method field - treat empty string as null
            if 'payment_method' in request.data:
                payment_method_value = request.data.get('payment_method')
                if payment_method_value == '' or payment_method_value is None:
                    instance.payment_method = None
                else:
                    instance.payment_method = validated_data.get('payment_method')
        
        # Update other fields
        for attr, value in validated_data.items():
            if attr not in ['store', 'payment_method']:
                setattr(instance, attr, value)
        
        instance.save()
        return instance
    
    class Meta:
        model = Expense
        fields = [
            'id', 'expense_number', 'category', 'category_name', 'store',
            'expense_date', 'description', 'amount', 'beneficiary',
            'payment_method', 'payment_reference', 'payment_date',
            'status', 'status_display', 'is_paid', 'approved_by',
            'approval_date', 'receipt', 'notes', 'created_at'
        ]