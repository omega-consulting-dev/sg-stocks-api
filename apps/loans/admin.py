from django.contrib import admin
from apps.loans.models import Loan, LoanPayment, LoanSchedule

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['loan_number', 'lender_name', 'principal_amount', 'total_amount', 'paid_amount', 'status']
    list_filter = ['loan_type', 'status']


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'loan', 'payment_date', 'amount']
    list_filter = ['payment_date', 'payment_method']


@admin.register(LoanSchedule)
class LoanScheduleAdmin(admin.ModelAdmin):
    list_display = ['loan', 'installment_number', 'due_date', 'total_amount', 'paid_amount', 'status']
    list_filter = ['status']