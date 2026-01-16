"""
Script pour supprimer toutes les données de test d'un tenant spécifique.
Supprime: Achats, Transferts, Ventes/Factures, Mouvements de stock, Paiements
Conserve: Produits, Stores, Clients, Fournisseurs, Utilisateurs
"""
import os
import django
import sys

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import transaction
from django_tenants.utils import tenant_context
from apps.tenants.models import Company
from apps.inventory.models import StockMovement, StockTransfer, Stock
from apps.invoicing.models import Invoice
from apps.suppliers.models import PurchaseOrder, SupplierPayment
from apps.sales.models import Sale

def reset_tenant_data(tenant_schema_name):
    """Supprime toutes les données transactionnelles d'un tenant."""
    
    try:
        # Récupérer le tenant
        tenant = Company.objects.get(schema_name=tenant_schema_name)
        print(f"\n{'='*60}")
        print(f"RÉINITIALISATION DES DONNÉES DU TENANT: {tenant.name}")
        print(f"Schema: {tenant.schema_name}")
        print(f"{'='*60}\n")
        
        # Demander confirmation
        confirmation = input(f"⚠️  ATTENTION: Cette action va supprimer TOUTES les données transactionnelles de '{tenant.name}'.\n"
                           f"Tapez exactement '{tenant.schema_name}' pour confirmer: ")
        
        if confirmation != tenant.schema_name:
            print("❌ Annulation. Le nom du tenant ne correspond pas.")
            return
        
        # Exécuter dans le contexte du tenant
        with tenant_context(tenant):
            with transaction.atomic():
                print("\n🗑️  Suppression des données en cours...\n")
                
                # 1. Supprimer les ventes
                sales_count = Sale.objects.all().count()
                Sale.objects.all().delete()
                print(f"✓ Ventes supprimées: {sales_count}")
                
                # 2. Supprimer les factures
                invoices_count = Invoice.objects.all().count()
                Invoice.objects.all().delete()
                print(f"✓ Factures supprimées: {invoices_count}")
                
                # 3. Supprimer les paiements fournisseurs
                supplier_payments_count = SupplierPayment.objects.all().count()
                SupplierPayment.objects.all().delete()
                print(f"✓ Paiements fournisseurs supprimés: {supplier_payments_count}")
                
                # 4. Supprimer les bons de commande
                purchase_orders_count = PurchaseOrder.objects.all().count()
                PurchaseOrder.objects.all().delete()
                print(f"✓ Bons de commande supprimés: {purchase_orders_count}")
                
                # 5. Supprimer les transferts de stock
                transfers_count = StockTransfer.objects.all().count()
                StockTransfer.objects.all().delete()
                print(f"✓ Transferts de stock supprimés: {transfers_count}")
                
                # 6. Supprimer les mouvements de stock
                movements_count = StockMovement.objects.all().count()
                StockMovement.objects.all().delete()
                print(f"✓ Mouvements de stock supprimés: {movements_count}")
                
                # 7. Réinitialiser les stocks à zéro
                stocks_count = Stock.objects.all().count()
                Stock.objects.all().update(quantity=0, reserved_quantity=0)
                print(f"✓ Stocks réinitialisés à zéro: {stocks_count}")
                
                print(f"\n{'='*60}")
                print("✅ RÉINITIALISATION TERMINÉE AVEC SUCCÈS")
                print(f"{'='*60}\n")
                print("📊 Résumé:")
                print(f"   - Ventes: {sales_count}")
                print(f"   - Factures: {invoices_count}")
                print(f"   - Paiements fournisseurs: {supplier_payments_count}")
                print(f"   - Bons de commande: {purchase_orders_count}")
                print(f"   - Transferts: {transfers_count}")
                print(f"   - Mouvements de stock: {movements_count}")
                print(f"   - Stocks réinitialisés: {stocks_count}")
                print()
                
    except Company.DoesNotExist:
        print(f"❌ Erreur: Le tenant '{tenant_schema_name}' n'existe pas.")
        print("\n📋 Tenants disponibles:")
        for t in Company.objects.exclude(schema_name='public'):
            print(f"   - {t.schema_name} ({t.name})")
    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Par défaut, utiliser 'saker'
    tenant_name = 'saker'
    
    # Permettre de passer le nom du tenant en argument
    if len(sys.argv) > 1:
        tenant_name = sys.argv[1]
    
    reset_tenant_data(tenant_name)
