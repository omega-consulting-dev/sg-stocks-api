from rest_framework import serializers
from apps.loans.models import Loan, LoanPayment, LoanSchedule


class LoanScheduleSerializer(serializers.ModelSerializer):
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LoanSchedule
        fields = [
            'id', 'installment_number', 'due_date', 'principal_amount',
            'interest_amount', 'total_amount', 'paid_amount', 'balance_due',
            'status', 'payment_date', 'is_overdue'
        ]


class LoanPaymentSerializer(serializers.ModelSerializer):
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LoanPayment
        fields = [
            'id', 'payment_number', 'loan', 'payment_date', 'amount',
            'principal_amount', 'interest_amount', 'payment_method', 'payment_method_display',
            'reference', 'notes', 'created_by_name', 'created_at'
        ]
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class LoanListSerializer(serializers.ModelSerializer):
    loan_type_display = serializers.CharField(source='get_loan_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Loan
        fields = [
            'id', 'loan_number', 'lender_name', 'loan_type', 'loan_type_display',
            'principal_amount', 'interest_rate', 'duration_months', 'start_date',
            'total_amount', 'paid_amount', 'balance_due', 'status', 'status_display', 'store'
        ]


class LoanDetailSerializer(serializers.ModelSerializer):
    schedule = LoanScheduleSerializer(many=True, read_only=True)
    payments = LoanPaymentSerializer(many=True, read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_fully_paid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Loan
        fields = [
            'id', 'loan_number', 'loan_type', 'lender_name', 'lender_contact', 'store',
            'principal_amount', 'interest_rate', 'duration_months', 'start_date',
            'end_date', 'status', 'total_amount', 'paid_amount', 'balance_due',
            'is_fully_paid', 'purpose', 'notes', 'schedule', 'payments',
            'created_at', 'updated_at'
        ]


class LoanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = [
            'loan_type', 'lender_name', 'lender_contact', 'principal_amount',
            'interest_rate', 'duration_months', 'start_date', 'end_date', 'purpose', 'notes', 'store'
        ]
    
    def create(self, validated_data):
        # Generate loan number
        last_loan = Loan.objects.order_by('-id').first()
        if last_loan and last_loan.loan_number:
            try:
                last_number = int(last_loan.loan_number.replace('LOAN', ''))
                next_number = last_number + 1
            except (ValueError, AttributeError):
                next_number = Loan.objects.count() + 1
        else:
            next_number = 1
        
        loan_number = f"LOAN{next_number:06d}"
        while Loan.objects.filter(loan_number=loan_number).exists():
            next_number += 1
            loan_number = f"LOAN{next_number:06d}"
        
        validated_data['loan_number'] = loan_number
        
        # Note: created_by sera défini par perform_create dans le ViewSet
        loan = super().create(validated_data)
        
        # Calculate total amount
        loan.calculate_total_amount()
        loan.save()
        
        # Generate schedule
        self._generate_schedule(loan)
        
        return loan
    
    def update(self, instance, validated_data):
        # Update all fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Recalculate total amount with new values
        instance.calculate_total_amount()
        instance.save()
        
        return instance
    
    def _generate_schedule(self, loan):
        """Generate loan repayment schedule."""
        from dateutil.relativedelta import relativedelta
        
        monthly_payment = loan.calculate_monthly_payment()
        
        for i in range(loan.duration_months):
            due_date = loan.start_date + relativedelta(months=i+1)
            
            # Simple calculation (can be improved with amortization formula)
            interest = (loan.principal_amount * loan.interest_rate / 100) / loan.duration_months
            principal = monthly_payment - interest
            
            LoanSchedule.objects.create(
                loan=loan,
                installment_number=i + 1,
                due_date=due_date,
                principal_amount=principal,
                interest_amount=interest,
                total_amount=monthly_payment
            )