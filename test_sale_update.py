import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.sales.models import Sale
from apps.inventory.models import StockMovement
from datetime import date

def test_sale_update(schema_name):
    """
    Test que la modification de l'année de sale_date met à jour automatiquement
    le sale_number et les références des mouvements
    """
    with schema_context(schema_name):
        print(f"\n{'='*60}")
        print(f"Test de mise à jour automatique pour: {schema_name}")
        print(f"{'='*60}\n")
        
        # Trouver la vente VTE2026000001
        try:
            sale = Sale.objects.get(sale_number='VTE2026000001')
            print(f"Vente trouvée: {sale.sale_number}")
            print(f"Date actuelle: {sale.sale_date}")
            print(f"Année actuelle: {sale.sale_date.year}")
            
            # Chercher les mouvements associés
            movements_before = StockMovement.objects.filter(reference=sale.sale_number)
            print(f"Mouvements trouvés avec référence {sale.sale_number}: {movements_before.count()}")
            
            # Modifier la date pour changer l'année (2026 -> 2025)
            # Créer une nouvelle date en 2025 (garder le mois/jour si possible)
            old_date = sale.sale_date
            new_date = date(2025, old_date.month, old_date.day)
            
            print(f"\nModification de la date: {old_date} -> {new_date}")
            sale.sale_date = new_date
            sale.save()
            
            # Recharger depuis la DB
            sale.refresh_from_db()
            
            print(f"\n✅ Après mise à jour:")
            print(f"  - Nouveau numéro: {sale.sale_number}")
            print(f"  - Nouvelle date: {sale.sale_date}")
            
            # Vérifier les mouvements
            movements_after = StockMovement.objects.filter(reference=sale.sale_number)
            print(f"  - Mouvements avec nouvelle référence: {movements_after.count()}")
            
            # Vérifier qu'il n'y a plus de mouvements avec l'ancienne référence
            old_movements = StockMovement.objects.filter(reference='VTE2026000001')
            print(f"  - Mouvements avec ancienne référence: {old_movements.count()}")
            
            if old_movements.count() == 0 and movements_after.count() > 0:
                print("\n✅ SUCCESS: Le numéro de vente et les références des mouvements ont été mis à jour automatiquement!")
            else:
                print("\n⚠️  WARNING: Vérifiez les résultats ci-dessus")
                
        except Sale.DoesNotExist:
            print("❌ Vente VTE2026000001 non trouvée")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_sale_update.py <schema_name>")
        print("Exemple: python test_sale_update.py agribio")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    
    # Vérifier que le tenant existe
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        print(f"Tenant trouvé: {tenant.name} ({schema_name})")
        test_sale_update(schema_name)
    except Company.DoesNotExist:
        print(f"❌ Erreur: Le tenant '{schema_name}' n'existe pas")
        sys.exit(1)
