import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.inventory.models import StockTransfer
from django.db.models import Q

def fix_transfer_numbers(schema_name):
    """
    Corrige les numéros de transfert pour utiliser l'année de transfer_date
    au lieu de l'année de creation
    """
    with schema_context(schema_name):
        print(f"\n{'='*60}")
        print(f"Correction des numéros de transfert pour: {schema_name}")
        print(f"{'='*60}\n")
        
        # Grouper les transferts par année de transfer_date
        transfers_by_year = {}
        for transfer in StockTransfer.objects.all().order_by('transfer_date'):
            year = transfer.transfer_date.year
            if year not in transfers_by_year:
                transfers_by_year[year] = []
            transfers_by_year[year].append(transfer)
        
        updated_count = 0
        error_count = 0
        
        # Pour chaque année, regénérer les numéros dans l'ordre chronologique
        for year in sorted(transfers_by_year.keys()):
            transfers = transfers_by_year[year]
            print(f"\nAnnée {year}: {len(transfers)} transfert(s)")
            print("-" * 40)
            
            for index, transfer in enumerate(transfers, start=1):
                old_number = transfer.transfer_number
                new_number = f"TR{year}{index:05d}"
                
                # Vérifier si le numéro a déjà la bonne année
                if old_number.startswith(f"TR{year}"):
                    # Peut-être juste un réordonnancement nécessaire
                    if old_number != new_number:
                        try:
                            transfer.transfer_number = new_number
                            transfer.save()
                            print(f"✅ {old_number} → {new_number} (réordonnancement)")
                            updated_count += 1
                        except Exception as e:
                            print(f"❌ Erreur pour {old_number}: {e}")
                            error_count += 1
                    else:
                        print(f"✓  {old_number} - Déjà correct")
                else:
                    # Changement d'année nécessaire
                    try:
                        transfer.transfer_number = new_number
                        transfer.save()
                        print(f"✅ {old_number} → {new_number} (année corrigée)")
                        updated_count += 1
                    except Exception as e:
                        print(f"❌ Erreur pour {old_number}: {e}")
                        error_count += 1
        
        print(f"\n{'='*60}")
        print(f"Résumé:")
        print(f"  - Numéros mis à jour: {updated_count}")
        print(f"  - Erreurs: {error_count}")
        print(f"{'='*60}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_transfer_numbers.py <schema_name>")
        print("Exemple: python fix_transfer_numbers.py agribio")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    
    # Vérifier que le tenant existe
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        print(f"Tenant trouvé: {tenant.name} ({schema_name})")
        fix_transfer_numbers(schema_name)
    except Company.DoesNotExist:
        print(f"❌ Erreur: Le tenant '{schema_name}' n'existe pas")
        sys.exit(1)
