from rest_framework import serializers
from apps.expenses.models import Expense, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer):
    def validate_code(self, value):
        """Validate that code is unique among active expense categories."""
        instance = self.instance
        queryset = ExpenseCategory.objects.filter(code=value, is_active=True)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Une catégorie de dépense avec ce code existe déjà.")
        return value
    
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
    
    def create(self, validated_data):
        """Override create to handle bank/cash payments"""
        payment_method = validated_data.get('payment_method')
        status = validated_data.get('status', 'draft')
        store = validated_data.get('store')
        amount = validated_data.get('amount')
        
        # Si la dépense est créée avec statut paid et un mode de paiement
        if status == 'paid' and payment_method:
            # Vérifier que le store est défini
            if not store:
                raise serializers.ValidationError({
                    'store': 'Un point de vente est requis pour les paiements.'
                })
            
            # Vérifier le solde pour cash
            if payment_method == 'cash':
                from apps.cashbox.utils import get_cashbox_real_balance
                real_balance = get_cashbox_real_balance(store_id=store.id)
                
                if real_balance < amount:
                    raise serializers.ValidationError({
                        'amount': f'Solde insuffisant dans la caisse. Solde disponible : {real_balance:,.0f} FCFA'
                    })
            
            # Vérifier le solde pour virement bancaire
            elif payment_method == 'bank_transfer':
                from apps.cashbox.utils import get_bank_balance
                bank_balance = get_bank_balance(store_id=store.id)
                
                if bank_balance < amount:
                    raise serializers.ValidationError({
                        'amount': f'Solde bancaire insuffisant. Solde disponible : {bank_balance:,.0f} FCFA'
                    })
        
        # Créer la dépense
        expense = Expense.objects.create(**validated_data)
        
        # Note: Pas besoin de créer de CashMovement pour les virements bancaires
        # Le modèle Expense avec payment_method='bank_transfer' suffit pour le calcul du solde
        
        return expense
    
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