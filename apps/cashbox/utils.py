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
    
    # 2. Ventes payées en espèces uniquement
    sales_qs = Sale.objects.filter(payment_method='cash')
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
    # Exclure les mouvements de type loan_payment et supplier_payment pour éviter le double comptage
    # car ils sont déjà comptés via LoanPayment et SupplierPayment
    cash_movements_out_qs = CashMovement.objects.filter(movement_type='out').exclude(
        category__in=['loan_payment', 'supplier_payment']
    )
    if store_id:
        cash_movements_out_qs = cash_movements_out_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_cash_movements_out = cash_movements_out_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_sorties = total_expenses + total_supplier_payments + total_loan_payments + total_cash_movements_out
    
    # Solde = Encaissements - Sorties
    return total_encaissements - total_sorties


def get_bank_balance(store_id=None):
    """
    Calcule le solde bancaire basé sur les transactions.
    
    Args:
        store_id: ID du point de vente (optionnel, si None calcule pour tous les stores)
    
    Returns:
        Decimal: Le solde bancaire calculé à partir des transactions
    """
    from apps.cashbox.models import CashMovement
    from apps.suppliers.models import SupplierPayment
    from apps.loans.models import LoanPayment
    from apps.expenses.models import Expense
    from apps.invoicing.models import InvoicePayment
    
    # Total des entrées d'argent en banque
    # 1. Dépôts bancaires depuis la caisse
    bank_deposits_qs = CashMovement.objects.filter(
        movement_type='out',
        category='bank_deposit'
    )
    if store_id:
        bank_deposits_qs = bank_deposits_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_bank_deposits = bank_deposits_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 2. Paiements de factures par carte bancaire
    invoice_payments_card_qs = InvoicePayment.objects.filter(
        payment_method='card',
        status='success'
    )
    if store_id:
        invoice_payments_card_qs = invoice_payments_card_qs.filter(invoice__store_id=store_id)
    total_invoice_payments_card = invoice_payments_card_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 3. Paiements de factures par virement bancaire
    invoice_payments_transfer_qs = InvoicePayment.objects.filter(
        payment_method='transfer',
        status='success'
    )
    if store_id:
        invoice_payments_transfer_qs = invoice_payments_transfer_qs.filter(invoice__store_id=store_id)
    total_invoice_payments_transfer = invoice_payments_transfer_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_entrees = total_bank_deposits + total_invoice_payments_card + total_invoice_payments_transfer
    
    # Total des sorties d'argent de la banque
    # 1. Retraits bancaires vers la caisse
    bank_withdrawals_qs = CashMovement.objects.filter(
        movement_type='in',
        category='bank_withdrawal'
    )
    if store_id:
        bank_withdrawals_qs = bank_withdrawals_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_bank_withdrawals = bank_withdrawals_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 2. Paiements fournisseurs par virement bancaire
    supplier_payments_bank_qs = SupplierPayment.objects.filter(payment_method='bank_transfer')
    if store_id:
        supplier_payments_bank_qs = supplier_payments_bank_qs.filter(
            Q(purchase_order__store_id=store_id) | Q(purchase_order__isnull=True)
        )
    total_supplier_payments_bank = supplier_payments_bank_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 3. Remboursements d'emprunts par virement bancaire
    loan_payments_bank_qs = LoanPayment.objects.filter(payment_method='bank_transfer')
    if store_id:
        loan_payments_bank_qs = loan_payments_bank_qs.filter(loan__store_id=store_id)
    total_loan_payments_bank = loan_payments_bank_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 4. Dépenses payées par virement bancaire
    expenses_bank_qs = Expense.objects.filter(status='paid', payment_method='bank_transfer')
    if store_id:
        expenses_bank_qs = expenses_bank_qs.filter(store_id=store_id)
    total_expenses_bank = expenses_bank_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_sorties = (total_bank_withdrawals + total_supplier_payments_bank + 
                     total_loan_payments_bank + total_expenses_bank)
    
    # Solde bancaire = Entrées - Sorties
    return total_entrees - total_sorties


def get_mobile_money_balance(store_id=None):
    """
    Calcule le solde Mobile Money (MTN/Orange) basé sur les transactions.
    
    Args:
        store_id: ID du point de vente (optionnel, si None calcule pour tous les stores)
    
    Returns:
        Decimal: Le solde Mobile Money calculé à partir des transactions
    """
    from apps.cashbox.models import CashMovement
    from apps.suppliers.models import SupplierPayment
    from apps.loans.models import LoanPayment
    from apps.expenses.models import Expense
    from apps.invoicing.models import InvoicePayment
    
    # Total des entrées d'argent en Mobile Money
    # 1. Dépôts Mobile Money depuis la caisse
    mm_deposits_qs = CashMovement.objects.filter(
        movement_type='out',
        category='mobile_money_deposit'
    )
    if store_id:
        mm_deposits_qs = mm_deposits_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_mm_deposits = mm_deposits_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 2. Paiements de factures par Mobile Money
    invoice_payments_mm_qs = InvoicePayment.objects.filter(
        payment_method='mobile_money',
        status='success'
    )
    if store_id:
        invoice_payments_mm_qs = invoice_payments_mm_qs.filter(invoice__store_id=store_id)
    total_invoice_payments_mm = invoice_payments_mm_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_entrees = total_mm_deposits + total_invoice_payments_mm
    
    # Total des sorties d'argent de Mobile Money
    # 1. Retraits Mobile Money vers la caisse
    mm_withdrawals_qs = CashMovement.objects.filter(
        movement_type='in',
        category='mobile_money_withdrawal'
    )
    if store_id:
        mm_withdrawals_qs = mm_withdrawals_qs.filter(cashbox_session__cashbox__store_id=store_id)
    total_mm_withdrawals = mm_withdrawals_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 2. Paiements fournisseurs par Mobile Money
    supplier_payments_mm_qs = SupplierPayment.objects.filter(payment_method='mobile_money')
    if store_id:
        supplier_payments_mm_qs = supplier_payments_mm_qs.filter(
            Q(purchase_order__store_id=store_id) | Q(purchase_order__isnull=True)
        )
    total_supplier_payments_mm = supplier_payments_mm_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 3. Remboursements d'emprunts par Mobile Money
    loan_payments_mm_qs = LoanPayment.objects.filter(payment_method='mobile_money')
    if store_id:
        loan_payments_mm_qs = loan_payments_mm_qs.filter(loan__store_id=store_id)
    total_loan_payments_mm = loan_payments_mm_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 4. Dépenses payées par Mobile Money
    expenses_mm_qs = Expense.objects.filter(status='paid', payment_method='mobile_money')
    if store_id:
        expenses_mm_qs = expenses_mm_qs.filter(store_id=store_id)
    total_expenses_mm = expenses_mm_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_sorties = (total_mm_withdrawals + total_supplier_payments_mm + 
                     total_loan_payments_mm + total_expenses_mm)
    
    # Solde Mobile Money = Entrées - Sorties
    return total_entrees - total_sorties
