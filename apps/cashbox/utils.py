"""
Utilitaires pour le calcul du solde de caisse basé sur les transactions réelles.
"""
from django.db.models import Sum, Q
from decimal import Decimal


def get_cashbox_real_balance(store_id=None):
    """
    Calcule le solde réel de la caisse basé sur les transactions.
    
    Args:
        store_id: ID du point de vente (optionnel, si None calcule pour tous les stores)
    
    Returns:
        Decimal: Le solde réel calculé à partir des transactions
    """
    from apps.invoicing.models import InvoicePayment
    from apps.sales.models import Sale
    from apps.expenses.models import Expense
    from apps.suppliers.models import SupplierPayment
    from apps.loans.models import LoanPayment
    from apps.cashbox.models import CashMovement
    
    # Total des encaissements (entrées d'argent)
    # 1. Paiements de factures en espèces
    invoice_payments_qs = InvoicePayment.objects.filter(payment_method='cash')
    if store_id:
        invoice_payments_qs = invoice_payments_qs.filter(invoice__store_id=store_id)
    total_invoice_payments = invoice_payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 2. Ventes payées
    sales_qs = Sale.objects.all()
    if store_id:
        sales_qs = sales_qs.filter(store_id=store_id)
    total_sales = sales_qs.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
    
    # 3. Mouvements de caisse entrants
    cash_movements_in_qs = CashMovement.objects.filter(movement_type='in')
    if store_id:
        cash_movements_in_qs = cash_movements_in_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_cash_movements_in = cash_movements_in_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_encaissements = total_invoice_payments + total_sales + total_cash_movements_in
    
    # Total des sorties d'argent
    # 1. Dépenses payées en espèces
    expenses_qs = Expense.objects.filter(status='paid', payment_method='cash')
    if store_id:
        expenses_qs = expenses_qs.filter(store_id=store_id)
    total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 2. Paiements fournisseurs en espèces
    supplier_payments_qs = SupplierPayment.objects.filter(payment_method='cash')
    if store_id:
        supplier_payments_qs = supplier_payments_qs.filter(
            Q(purchase_order__store_id=store_id) | Q(purchase_order__isnull=True)
        )
    total_supplier_payments = supplier_payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 3. Remboursements d'emprunts en espèces
    loan_payments_qs = LoanPayment.objects.filter(payment_method='cash')
    if store_id:
        loan_payments_qs = loan_payments_qs.filter(loan__store_id=store_id)
    total_loan_payments = loan_payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 4. Décaissements (mouvements de caisse sortants)
    cash_movements_out_qs = CashMovement.objects.filter(movement_type='out')
    if store_id:
        cash_movements_out_qs = cash_movements_out_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_cash_movements_out = cash_movements_out_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_sorties = total_expenses + total_supplier_payments + total_loan_payments + total_cash_movements_out
    
    # Solde = Encaissements - Sorties
    return total_encaissements - total_sorties
