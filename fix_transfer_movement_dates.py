"""
Script pour corriger les dates des mouvements de stock de transfert
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.inventory.models import StockMovement, StockTransfer

def fix_transfer_movement_dates(schema_name):
    """Corriger les dates des mouvements de transfert pour utiliser transfer_date"""
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
    except Company.DoesNotExist:
        print(f"❌ Tenant '{schema_name}' n'existe pas")
        return
    
    with schema_context(schema_name):
        print(f"\n🔍 Recherche des mouvements de transfert dans {schema_name}...")
        
        # Récupérer tous les mouvements de transfert qui ont une référence de type TR
        transfer_movements = StockMovement.objects.filter(
            reference__startswith='TR'
        ).order_by('reference')
        
        print(f"✅ Trouvé {transfer_movements.count()} mouvements de transfert")
        
        updated_count = 0
        errors_count = 0
        
        for movement in transfer_movements:
            try:
                # Extraire le numéro de transfert de la référence
                transfer_number = movement.reference
                
                # Trouver le transfert correspondant
                try:
                    transfer = StockTransfer.objects.get(transfer_number=transfer_number)
                    
                    # Vérifier si la date est différente
                    if movement.date != transfer.transfer_date:
                        old_date = movement.date
                        movement.date = transfer.transfer_date
                        movement.save()
                        
                        print(f"✅ {movement.id} - {transfer_number}: {old_date} → {transfer.transfer_date}")
                        updated_count += 1
                    else:
                        print(f"⏭️  {movement.id} - {transfer_number}: Date déjà correcte ({movement.date})")
                        
                except StockTransfer.DoesNotExist:
                    print(f"⚠️  {movement.id} - {transfer_number}: Transfert non trouvé")
                    errors_count += 1
                    
            except Exception as e:
                print(f"❌ Erreur pour le mouvement {movement.id}: {e}")
                errors_count += 1
        
        print(f"\n📊 Résumé:")
        print(f"   ✅ Mouvements mis à jour: {updated_count}")
        print(f"   ⚠️  Erreurs: {errors_count}")
        print(f"   📦 Total traité: {transfer_movements.count()}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_transfer_movement_dates.py <schema_name>")
        print("Exemple: python fix_transfer_movement_dates.py agribio")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    fix_transfer_movement_dates(schema_name)
