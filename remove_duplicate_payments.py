"""
Script to remove duplicate loan payments
Usage: python remove_duplicate_payments.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.loans.models import Loan, LoanPayment
from django.db import models
from decimal import Decimal
from collections import defaultdict

def run():
    """Remove duplicate loan payments based on loan, date, and amount."""
    
    total_deleted = 0
    loans_affected = []
    
    print("\n🚀 Starting duplicate payment removal...\n")
    
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
                
                print(f"\n🔍 Found {len(to_delete)} duplicate(s) for loan {loan.loan_number}")
                print(f"   Date: {key[0]}, Amount: {key[1]}")
                print(f"   Keeping: {to_keep.payment_number} (created: {to_keep.created_at})")
                
                for dup in to_delete:
                    print(f"   Deleting: {dup.payment_number} (created: {dup.created_at})")
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
            loan.balance_due = loan.total_amount - total_paid
            
            # Update status
            if loan.balance_due <= 0:
                loan.status = 'paid'
                loan.is_fully_paid = True
            else:
                loan.status = 'active'
                loan.is_fully_paid = False
            
            loan.save()
            print(f"   ✅ Recalculated: Paid={loan.paid_amount}, Balance={loan.balance_due}")
    
    print(f"\n{'='*60}")
    print(f"✅ SUMMARY:")
    print(f"   Total duplicate payments deleted: {total_deleted}")
    print(f"   Loans affected: {len(loans_affected)}")
    if loans_affected:
        print(f"   Loan numbers: {', '.join(loans_affected)}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    run()
    print("✨ Done!")

if __name__ == '__main__':
    run()

