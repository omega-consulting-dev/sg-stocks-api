"""
Script pour corriger le numéro de vente VTE2026000001 vers VTE2025000001
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.sales.models import Sale

def fix_sale_number(schema_name):
    """Corriger le numéro de vente pour correspondre à l'année de sale_date"""
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
    except Company.DoesNotExist:
        print(f"❌ Tenant '{schema_name}' n'existe pas")
        return
    
    with schema_context(schema_name):
        print(f"\n🔍 Recherche de la vente VTE2026000001 dans {schema_name}...")
        
        try:
            sale = Sale.objects.get(sale_number='VTE2026000001')
            print(f"✅ Vente trouvée:")
            print(f"   ID: {sale.id}")
            print(f"   Numéro actuel: {sale.sale_number}")
            print(f"   Date de vente: {sale.sale_date}")
            print(f"   Année de la date: {sale.sale_date.year}")
            
            # Calculer le nouveau numéro basé sur l'année de sale_date
            sale_year = sale.sale_date.year
            new_number = f"VTE{sale_year}000001"
            
            print(f"\n🔄 Modification du numéro:")
            print(f"   Ancien: {sale.sale_number}")
            print(f"   Nouveau: {new_number}")
            
            # Vérifier si le nouveau numéro existe déjà
            if Sale.objects.filter(sale_number=new_number).exists():
                print(f"❌ ERREUR: Le numéro {new_number} existe déjà!")
                return
            
            # Mettre à jour
            sale.sale_number = new_number
            sale.save()
            
            print(f"✅ Numéro mis à jour avec succès!")
            
            # Vérifier
            sale.refresh_from_db()
            print(f"\n✓ Vérification:")
            print(f"   Numéro en BD: {sale.sale_number}")
            
        except Sale.DoesNotExist:
            print(f"❌ Vente VTE2026000001 non trouvée dans {schema_name}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_sale_number.py <schema_name>")
        print("Exemple: python fix_sale_number.py agribio")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    fix_sale_number(schema_name)
