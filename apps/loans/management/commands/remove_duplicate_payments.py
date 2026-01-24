"""
Management command to remove duplicate loan payments
Usage: python manage.py remove_duplicate_payments --schema=saker
"""

from django.core.management.base import BaseCommand
from django.db import connection, models
from apps.loans.models import Loan, LoanPayment
from decimal import Decimal
from collections import defaultdict


class Command(BaseCommand):
    help = 'Remove duplicate loan payments based on loan, date, and amount'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Tenant schema name (e.g., saker, agribio, demo)',
            required=True
        )

    def handle(self, *args, **options):
        schema_name = options['schema']
        
        # Set the schema
        connection.set_schema(schema_name)
        
        self.stdout.write(self.style.SUCCESS(f'\n🚀 Starting duplicate payment removal for schema: {schema_name}\n'))
        
        total_deleted = 0
        loans_affected = []
        
        # Get all loans
        loans = Loan.objects.all()
        
        for loan in loans:
            payments = LoanPayment.objects.filter(loan=loan).order_by('created_at')
            
            # Group payments by date and amount
            payment_groups = defaultdict(list)
            for payment in payments:
                key = (payment.payment_date, payment.amount)
                payment_groups[key].append(payment)
            
            # Find and delete duplicates
            loan_deleted = 0
            for key, group in payment_groups.items():
                if len(group) > 1:
                    # Keep the first payment (oldest by created_at), delete the rest
                    to_keep = group[0]
                    to_delete = group[1:]
                    
                    self.stdout.write(f"\n🔍 Found {len(to_delete)} duplicate(s) for loan {loan.loan_number}")
                    self.stdout.write(f"   Date: {key[0]}, Amount: {key[1]}")
                    self.stdout.write(f"   Keeping: {to_keep.payment_number} (created: {to_keep.created_at})")
                    
                    for dup in to_delete:
                        self.stdout.write(self.style.WARNING(f"   Deleting: {dup.payment_number} (created: {dup.created_at})"))
                        dup.delete()
                        loan_deleted += 1
                        total_deleted += 1
            
            if loan_deleted > 0:
                loans_affected.append(loan.loan_number)
                
                # Recalculate paid amount
                total_paid = LoanPayment.objects.filter(loan=loan).aggregate(
                    total=models.Sum('amount')
                )['total'] or Decimal('0')
                
                loan.paid_amount = total_paid
                
                # Update status based on balance
                balance = loan.total_amount - total_paid
                if balance <= 0:
                    loan.status = 'paid'
                else:
                    loan.status = 'active'
                
                loan.save()
                self.stdout.write(self.style.SUCCESS(f"   ✅ Recalculated: Paid={loan.paid_amount}, Balance={balance}"))
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS('✅ SUMMARY:'))
        self.stdout.write(f"   Total duplicate payments deleted: {total_deleted}")
        self.stdout.write(f"   Loans affected: {len(loans_affected)}")
        if loans_affected:
            self.stdout.write(f"   Loan numbers: {', '.join(loans_affected)}")
        self.stdout.write(f"{'='*60}\n")
        self.stdout.write(self.style.SUCCESS('✨ Done!'))
