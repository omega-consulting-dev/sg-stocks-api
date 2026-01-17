import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.inventory.models import StockTransfer, StockMovement

def fix_movement_references(schema_name):
    """
    Met à jour les références des mouvements de stock pour correspondre
    aux nouveaux numéros de transfert (basés sur transfer_date year)
    """
    with schema_context(schema_name):
        print(f"\n{'='*60}")
        print(f"Mise à jour des références de mouvements pour: {schema_name}")
        print(f"{'='*60}\n")
        
        updated_count = 0
        error_count = 0
        checked_count = 0
        
        # Récupérer tous les transferts
        for transfer in StockTransfer.objects.all().order_by('transfer_date'):
            # Chercher les mouvements avec l'ancien format de référence
            # Les anciennes références commencent par TR2026 mais le transfert a une date en 2025
            transfer_year = transfer.transfer_date.year
            current_number = transfer.transfer_number
            
            # Chercher les mouvements liés à ce transfert
            # Ils peuvent avoir soit l'ancien numéro soit le nouveau
            movements = StockMovement.objects.filter(
                reference__startswith='TR'
            ).filter(
                product__in=[line.product for line in transfer.lines.all()],
                date=transfer.transfer_date
            )
            
            for movement in movements:
                checked_count += 1
                old_ref = movement.reference
                
                # Vérifier si la référence doit être mise à jour
                if old_ref and old_ref.startswith('TR') and old_ref != current_number:
                    # Extraire le numéro sans le préfixe année
                    # Exemple: TR202600001 ou TR202500001
                    if len(old_ref) >= 11:  # TR + 4 digits year + 5 digits number
                        # Vérifier si c'est potentiellement l'ancien numéro de ce transfert
                        # En cherchant les mouvements qui correspondent aux produits et dates
                        try:
                            movement.reference = current_number
                            movement.save()
                            print(f"✅ Mouvement #{movement.id}: {old_ref} → {current_number}")
                            updated_count += 1
                        except Exception as e:
                            print(f"❌ Erreur pour mouvement #{movement.id}: {e}")
                            error_count += 1
                    
        # Approche alternative: chercher directement par pattern d'ancienne référence
        print("\n" + "-"*60)
        print("Recherche des références avec mauvaise année...")
        print("-"*60 + "\n")
        
        # Chercher tous les mouvements avec des références TR2026
        old_movements = StockMovement.objects.filter(reference__startswith='TR2026')
        
        for movement in old_movements:
            old_ref = movement.reference
            
            # Extraire le numéro séquentiel (les 5 derniers chiffres)
            if len(old_ref) >= 11:
                seq_number = old_ref[-5:]  # Les 5 derniers chiffres
                
                # Essayer de trouver le transfert correspondant par sa date et ses produits
                # On cherche un transfert qui a ce mouvement
                try:
                    # Chercher le transfert avec cette date
                    transfer_year = movement.date.year if movement.date else 2025
                    new_ref = f"TR{transfer_year}{seq_number}"
                    
                    # Vérifier si un transfert avec ce nouveau numéro existe
                    if StockTransfer.objects.filter(transfer_number=new_ref).exists():
                        movement.reference = new_ref
                        movement.save()
                        print(f"✅ Mouvement #{movement.id}: {old_ref} → {new_ref}")
                        updated_count += 1
                    else:
                        print(f"⚠️  Mouvement #{movement.id}: Transfert {new_ref} introuvable")
                        
                except Exception as e:
                    print(f"❌ Erreur pour mouvement #{movement.id} ({old_ref}): {e}")
                    error_count += 1
        
        print(f"\n{'='*60}")
        print(f"Résumé:")
        print(f"  - Mouvements vérifiés: {checked_count}")
        print(f"  - Références mises à jour: {updated_count}")
        print(f"  - Erreurs: {error_count}")
        print(f"{'='*60}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_transfer_movement_references.py <schema_name>")
        print("Exemple: python fix_transfer_movement_references.py agribio")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    
    # Vérifier que le tenant existe
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        print(f"Tenant trouvé: {tenant.name} ({schema_name})")
        fix_movement_references(schema_name)
    except Company.DoesNotExist:
        print(f"❌ Erreur: Le tenant '{schema_name}' n'existe pas")
        sys.exit(1)
