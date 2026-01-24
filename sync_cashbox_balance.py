"""
Script pour synchroniser le solde actuel des caisses avec les transactions réelles.
Usage: python sync_cashbox_balance.py
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.cashbox.models import Cashbox, CashMovement
from apps.invoicing.models import InvoicePayment
from apps.sales.models import Sale
from apps.expenses.models import Expense
from apps.suppliers.models import SupplierPayment
from apps.loans.models import LoanPayment
from django.db import connection
from django.db.models import Sum, Q
from decimal import Decimal


def calculate_cashbox_balance(cashbox):
    """Calcule le solde réel d'une caisse basé sur toutes les transactions."""
    store = cashbox.store
    
    # ENCAISSEMENTS
    # 1. Paiements de factures en espèces pour ce store
    invoice_payments = InvoicePayment.objects.filter(
        invoice__store=store,
        payment_method='cash'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 2. Ventes payées (paid_amount) pour ce store
    sales_paid = Sale.objects.filter(
        store=store,
        payment_status__in=['paid', 'partial']
    ).aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
    
    total_encaissements = invoice_payments + sales_paid
    
    # SORTIES
    # 1. Dépenses payées en espèces avec ce store
    expenses = Expense.objects.filter(
        store=store,
        status='paid',
        payment_method='cash'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 2. Paiements fournisseurs en espèces
    supplier_payments = SupplierPayment.objects.filter(
        purchase_order__store=store,
        payment_method='cash'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # 3. Remboursements de prêts en espèces
    try:
        loan_payments = LoanPayment.objects.filter(
            loan__store=store,
            payment_method='cash'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    except:
        # Si le modèle ou champ n'existe pas encore
        loan_payments = Decimal('0')
    
    total_sorties = expenses + supplier_payments + loan_payments
    
    # Calcul du solde
    balance = total_encaissements - total_sorties
    
    return balance, total_encaissements, total_sorties


def sync_cashboxes_for_tenant(tenant):
    """Synchroniser les caisses pour un tenant."""
    connection.set_tenant(tenant)
    
    cashboxes = Cashbox.objects.select_related('store').all()
    
    print(f"\n📦 Tenant: {tenant.name} ({tenant.schema_name})")
    print(f"   Caisses trouvées: {cashboxes.count()}")
    
    updated_count = 0
    
    for cashbox in cashboxes:
        old_balance = cashbox.current_balance
        new_balance, encaissements, sorties = calculate_cashbox_balance(cashbox)
        
        if old_balance != new_balance:
            cashbox.current_balance = new_balance
            cashbox.save(update_fields=['current_balance'])
            updated_count += 1
            
            print(f"\n   🔄 {cashbox.code} - {cashbox.name}")
            print(f"      Store: {cashbox.store.name}")
            print(f"      Ancien solde: {old_balance:,.0f} FCFA")
            print(f"      Nouveau solde: {new_balance:,.0f} FCFA")
            print(f"      (Encaissements: {encaissements:,.0f} - Sorties: {sorties:,.0f})")
        else:
            print(f"   ✅ {cashbox.code} - Solde déjà correct: {old_balance:,.0f} FCFA")
    
    return updated_count


def main():
    """Point d'entrée principal."""
    print("=" * 70)
    print("💰 Synchronisation des soldes de caisses avec les transactions")
    print("=" * 70)
    
    # Importer le modèle Tenant
    from django_tenants.utils import get_tenant_model, get_public_schema_name
    
    Tenant = get_tenant_model()
    public_schema_name = get_public_schema_name()
    
    # Récupérer tous les tenants sauf le schéma public
    tenants = Tenant.objects.exclude(schema_name=public_schema_name)
    
    total_updated = 0
    
    for tenant in tenants:
        try:
            updated = sync_cashboxes_for_tenant(tenant)
            total_updated += updated
        except Exception as e:
            print(f"   ❌ Erreur pour {tenant.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"✅ Terminé! {total_updated} caisse(s) mise(s) à jour")
    print("=" * 70)


if __name__ == '__main__':
    main()
