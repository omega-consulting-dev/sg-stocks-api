#!/usr/bin/env python
"""
Script pour réinitialiser le tenant de démo.
À exécuter quotidiennement (via cron ou tâche planifiée) pour nettoyer les données.
"""
import os
import sys
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company

def reset_demo_tenant():
    """Réinitialiser le tenant de démo"""
    print("="*80)
    print(f"RÉINITIALISATION DU TENANT DE DÉMO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print()
    
    # Vérifier que le tenant démo existe
    demo = Company.objects.filter(schema_name='demo').first()
    if not demo:
        print("[ERREUR] Le tenant 'demo' n'existe pas!")
        return False
    
    print(f"[UPDATE] Réinitialisation du tenant: {demo.name}")
    print()
    
    with schema_context('demo'):
        from apps.sales.models import Sale, SaleLine, Quote, QuoteLine
        from apps.invoicing.models import Invoice, InvoiceLine, Payment
        from apps.inventory.models import Stock, StockMovement, StockTransfer, Inventory
        from apps.cashbox.models import CashboxTransaction
        from apps.loans.models import Loan, LoanPayment
        from apps.expenses.models import Expense
        from apps.suppliers.models import PurchaseOrder, SupplierPayment
        from apps.accounts.models import UserSession, UserActivity
        
        # Supprimer les transactions
        print("[SUPPRESSION]  Suppression des données transactionnelles...")
        
        counts = {
            'Ventes': Sale.objects.count(),
            'Devis': Quote.objects.count(),
            'Factures': Invoice.objects.count(),
            'Paiements': Payment.objects.count(),
            'Mouvements stock': StockMovement.objects.count(),
            'Transferts': StockTransfer.objects.count(),
            'Inventaires': Inventory.objects.count(),
            'Caisse': CashboxTransaction.objects.count(),
            'Prêts': Loan.objects.count(),
            'Dépenses': Expense.objects.count(),
            'Commandes fournisseur': PurchaseOrder.objects.count(),
            'Sessions': UserSession.objects.count(),
            'Activités': UserActivity.objects.count(),
        }
        
        # Afficher avant suppression
        print("\n   [STATS] Données à supprimer:")
        for model_name, count in counts.items():
            if count > 0:
                print(f"      - {model_name}: {count}")
        
        # Suppression
        print("\n   [SUPPRESSION]  Suppression en cours...")
        Sale.objects.all().delete()
        Quote.objects.all().delete()
        Invoice.objects.all().delete()
        Payment.objects.all().delete()
        StockMovement.objects.all().delete()
        StockTransfer.objects.all().delete()
        Inventory.objects.all().delete()
        CashboxTransaction.objects.all().delete()
        Loan.objects.all().delete()
        LoanPayment.objects.all().delete()
        Expense.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        SupplierPayment.objects.all().delete()
        UserSession.objects.all().delete()
        UserActivity.objects.all().delete()
        
        print("   [OK] Données transactionnelles supprimées")
        
        # Réinitialiser les stocks à zéro
        print("\n   [PACKAGE] Réinitialisation des stocks...")
        Stock.objects.all().update(quantity=0)
        print("   [OK] Stocks réinitialisés")
        
        # Réinitialiser le mot de passe admin
        print("\n   [LOCK] Réinitialisation du mot de passe admin...")
        from apps.accounts.models import User
        admin = User.objects.filter(email='demo@sgstock.cm').first()
        if admin:
            admin.set_password('demo1234')
            admin.save()
            print("   [OK] Mot de passe admin réinitialisé")
        
    print()
    print("="*80)
    print("[OK] TENANT DE DÉMO RÉINITIALISÉ AVEC SUCCÈS!")
    print("="*80)
    print()
    print("[INFO] Pour repeupler avec des données:")
    print("   python populate_demo_data.py")
    print()
    
    return True

if __name__ == '__main__':
    try:
        reset_demo_tenant()
    except Exception as e:
        print(f"[ERREUR] ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
