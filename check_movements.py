"""
Script pour vérifier les mouvements de stock dans un tenant.
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import tenant_context
from apps.tenants.models import Company
from apps.inventory.models import StockMovement

def check_movements(tenant_schema_name):
    try:
        tenant = Company.objects.get(schema_name=tenant_schema_name)
        print(f"\n{'='*60}")
        print(f"MOUVEMENTS DE STOCK - TENANT: {tenant.name}")
        print(f"{'='*60}\n")
        
        with tenant_context(tenant):
            movements = StockMovement.objects.all().order_by('-created_at')
            
            if movements.count() == 0:
                print("❌ Aucun mouvement de stock trouvé")
                return
            
            print(f"✅ {movements.count()} mouvement(s) trouvé(s)\n")
            
            for m in movements:
                print(f"📦 Mouvement #{m.id}")
                print(f"   Type: {m.movement_type} ({m.get_movement_type_display()})")
                print(f"   Produit: {m.product.name}")
                print(f"   Store: {m.store.name} (ID: {m.store.id})")
                print(f"   Quantité: {m.quantity}")
                print(f"   Référence: {m.reference}")
                print(f"   Date: {m.date if m.date else 'Non définie'}")
                print(f"   Créé le: {m.created_at}")
                print(f"   Facture: {m.invoice_id if m.invoice else 'Aucune'}")
                print(f"   Active: {m.is_active}")
                print()
                
    except Company.DoesNotExist:
        print(f"❌ Le tenant '{tenant_schema_name}' n'existe pas.")
        print("\n📋 Tenants disponibles:")
        for t in Company.objects.exclude(schema_name='public'):
            print(f"   - {t.schema_name} ({t.name})")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    tenant_name = 'agribio' if len(sys.argv) <= 1 else sys.argv[1]
    check_movements(tenant_name)
