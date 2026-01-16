"""
Script pour supprimer toutes les données de test (mouvements, transferts, ventes, achats)
et remettre les stocks à zéro.
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.settings.local')
django.setup()

from django.db import transaction
from apps.inventory.models import StockMovement, StockTransfer, Stock
from apps.invoicing.models import Invoice
from apps.suppliers.models import PurchaseOrder, SupplierPayment

def reset_all_data():
    """Supprime toutes les données de test et remet les stocks à zéro."""
    
    print("🗑️  Suppression de toutes les données de test...")
    
    with transaction.atomic():
        # 1. Supprimer les paiements fournisseurs
        payment_count = SupplierPayment.objects.count()
        SupplierPayment.objects.all().delete()
        print(f"✅ {payment_count} paiements fournisseurs supprimés")
        
        # 2. Supprimer les factures/ventes
        invoice_count = Invoice.objects.count()
        Invoice.objects.all().delete()
        print(f"✅ {invoice_count} factures supprimées")
        
        # 3. Supprimer les transferts de stock
        transfer_count = StockTransfer.objects.count()
        StockTransfer.objects.all().delete()
        print(f"✅ {transfer_count} transferts supprimés")
        
        # 4. Supprimer les bons de commande
        po_count = PurchaseOrder.objects.count()
        PurchaseOrder.objects.all().delete()
        print(f"✅ {po_count} bons de commande supprimés")
        
        # 5. Supprimer tous les mouvements de stock
        movement_count = StockMovement.objects.count()
        StockMovement.objects.all().delete()
        print(f"✅ {movement_count} mouvements de stock supprimés")
        
        # 6. Remettre tous les stocks à zéro
        stock_count = Stock.objects.count()
        Stock.objects.all().update(quantity=0, reserved_quantity=0)
        print(f"✅ {stock_count} stocks remis à zéro")
    
    print("\n✨ Toutes les données ont été supprimées avec succès!")
    print("Vous pouvez maintenant recommencer les tests.")

if __name__ == '__main__':
    print("⚠️  ATTENTION : Ce script va supprimer TOUTES les données suivantes:")
    print("   - Paiements fournisseurs")
    print("   - Factures/Ventes")
    print("   - Transferts de stock")
    print("   - Bons de commande")
    print("   - Mouvements de stock")
    print("   - Stocks (remis à zéro)")
    print()
    
    confirm = input("Êtes-vous sûr de vouloir continuer ? (tapez 'OUI' pour confirmer): ")
    
    if confirm.upper() == 'OUI':
        reset_all_data()
    else:
        print("❌ Opération annulée")
