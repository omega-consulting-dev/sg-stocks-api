import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.sales.models import Sale

def fix_sale_number(schema_name, old_sale_number):
    """
    Corrige un numéro de vente pour qu'il corresponde à l'année de sale_date
    """
    with schema_context(schema_name):
        print(f"\n{'='*60}")
        print(f"Correction du numéro de vente: {old_sale_number}")
        print(f"Tenant: {schema_name}")
        print(f"{'='*60}\n")
        
        try:
            # Trouver la vente
            sale = Sale.objects.get(sale_number=old_sale_number)
            
            print(f"Vente trouvée:")
            print(f"  - Numéro actuel: {sale.sale_number}")
            print(f"  - Date de vente: {sale.sale_date}")
            print(f"  - Client: {sale.customer.name if sale.customer else 'N/A'}")
            print(f"  - Montant: {sale.total_amount}")
            
            # Déterminer la bonne année
            sale_year = sale.sale_date.year
            
            # Extraire le numéro séquentiel actuel
            current_seq = int(old_sale_number.replace('VTE', '')[-6:])
            
            # Trouver le prochain numéro disponible pour cette année
            last_sale = Sale.objects.filter(
                sale_date__year=sale_year
            ).exclude(id=sale.id).order_by('-sale_number').first()
            
            if last_sale and last_sale.sale_number.startswith(f"VTE{sale_year}"):
                # Extraire le numéro du dernier sale de cette année
                last_number = int(last_sale.sale_number.replace(f"VTE{sale_year}", ''))
                next_number = last_number + 1
            else:
                # Compter les ventes de cette année
                count = Sale.objects.filter(
                    sale_date__year=sale_year
                ).exclude(id=sale.id).count()
                next_number = count + 1
            
            new_sale_number = f"VTE{sale_year}{next_number:06d}"
            
            print(f"\n  → Nouveau numéro: {new_sale_number}")
            
            # Mettre à jour
            sale.sale_number = new_sale_number
            sale.save()
            
            print(f"\n✅ Numéro de vente mis à jour avec succès!")
            print(f"   {old_sale_number} → {new_sale_number}")
            
        except Sale.DoesNotExist:
            print(f"❌ Erreur: La vente '{old_sale_number}' n'existe pas")
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python fix_single_sale_number.py <schema_name> <sale_number>")
        print("Exemple: python fix_single_sale_number.py agribio VTE2026000001")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    sale_number = sys.argv[2]
    
    # Vérifier que le tenant existe
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        print(f"Tenant trouvé: {tenant.name} ({schema_name})")
        fix_sale_number(schema_name, sale_number)
    except Company.DoesNotExist:
        print(f"❌ Erreur: Le tenant '{schema_name}' n'existe pas")
        sys.exit(1)
