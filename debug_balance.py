"""
Script de débogage pour analyser le solde de caisse
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.cashbox.utils import get_cashbox_real_balance
from apps.invoicing.models import InvoicePayment
from apps.sales.models import Sale
from apps.expenses.models import Expense
from apps.suppliers.models import SupplierPayment
from apps.loans.models import LoanPayment
from apps.cashbox.models import CashMovement
from django.db.models import Sum, Q
from decimal import Decimal

def debug_balance(store_id=None):
    """Affiche le détail du calcul du solde"""
    
    print("\n" + "="*60)
    print(f"ANALYSE DU SOLDE DE CAISSE - Store ID: {store_id or 'Tous'}")
    print("="*60)
    
    # === ENTRÉES ===
    print("\n--- ENTRÉES D'ARGENT ---")
    
    # 1. Paiements de factures en espèces
    invoice_payments_qs = InvoicePayment.objects.filter(payment_method='cash')
    if store_id:
        invoice_payments_qs = invoice_payments_qs.filter(invoice__store_id=store_id)
    total_invoice_payments = invoice_payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    count_invoice = invoice_payments_qs.count()
    print(f"1. Paiements factures (cash): {total_invoice_payments:,.2f} FCFA ({count_invoice} paiements)")
    
    # 2. Ventes payées
    sales_qs = Sale.objects.all()
    if store_id:
        sales_qs = sales_qs.filter(store_id=store_id)
    total_sales = sales_qs.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
    count_sales = sales_qs.count()
    print(f"2. Ventes: {total_sales:,.2f} FCFA ({count_sales} ventes)")
    
    # 3. Mouvements de caisse entrants
    cash_movements_in_qs = CashMovement.objects.filter(movement_type='in')
    if store_id:
        cash_movements_in_qs = cash_movements_in_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_cash_movements_in = cash_movements_in_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    count_cm_in = cash_movements_in_qs.count()
    print(f"3. Encaissements (CashMovement IN): {total_cash_movements_in:,.2f} FCFA ({count_cm_in} mouvements)")
    
    total_entrees = total_invoice_payments + total_sales + total_cash_movements_in
    print(f"\n→ TOTAL ENTRÉES: {total_entrees:,.2f} FCFA")
    
    # === SORTIES ===
    print("\n--- SORTIES D'ARGENT ---")
    
    # 1. Dépenses payées en espèces
    expenses_qs = Expense.objects.filter(status='paid', payment_method='cash')
    if store_id:
        expenses_qs = expenses_qs.filter(store_id=store_id)
    total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    count_expenses = expenses_qs.count()
    print(f"1. Dépenses (cash): {total_expenses:,.2f} FCFA ({count_expenses} dépenses)")
    
    # 2. Paiements fournisseurs en espèces
    supplier_payments_qs = SupplierPayment.objects.filter(payment_method='cash')
    if store_id:
        supplier_payments_qs = supplier_payments_qs.filter(
            Q(purchase_order__store_id=store_id) | Q(purchase_order__isnull=True)
        )
    total_supplier_payments = supplier_payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    count_supplier = supplier_payments_qs.count()
    print(f"2. Paiements fournisseurs (cash): {total_supplier_payments:,.2f} FCFA ({count_supplier} paiements)")
    
    # 3. Remboursements d'emprunts en espèces
    loan_payments_qs = LoanPayment.objects.filter(payment_method='cash')
    if store_id:
        loan_payments_qs = loan_payments_qs.filter(loan__store_id=store_id)
    total_loan_payments = loan_payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    count_loan = loan_payments_qs.count()
    print(f"3. Remboursements emprunts (cash): {total_loan_payments:,.2f} FCFA ({count_loan} paiements)")
    
    # 4. Décaissements (mouvements de caisse sortants)
    cash_movements_out_qs = CashMovement.objects.filter(movement_type='out')
    if store_id:
        cash_movements_out_qs = cash_movements_out_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_cash_movements_out = cash_movements_out_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    count_cm_out = cash_movements_out_qs.count()
    print(f"4. Décaissements (CashMovement OUT): {total_cash_movements_out:,.2f} FCFA ({count_cm_out} mouvements)")
    
    # Détail des décaissements
    if count_cm_out > 0:
        print("\n   Détail des décaissements:")
        for cm in cash_movements_out_qs:
            print(f"   - {cm.movement_number}: {cm.amount:,.2f} FCFA ({cm.category}) - {cm.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    total_sorties = total_expenses + total_supplier_payments + total_loan_payments + total_cash_movements_out
    print(f"\n→ TOTAL SORTIES: {total_sorties:,.2f} FCFA")
    
    # === SOLDE ===
    solde = total_entrees - total_sorties
    print("\n" + "="*60)
    print(f"SOLDE FINAL: {solde:,.2f} FCFA")
    print("="*60 + "\n")
    
    return solde

if __name__ == '__main__':
    # Analyser pour tous les stores
    debug_balance()
    
    # Si vous voulez analyser un store spécifique, décommentez:
    # debug_balance(store_id=1)
