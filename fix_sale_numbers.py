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
from django.db import transaction

def fix_incorrect_sale_numbers(schema_name):
    """
    Corrige les numéros de vente dont l'année ne correspond pas
    à l'année de sale_date
    """
    with schema_context(schema_name):
        print(f"\n{'='*60}")
        print(f"Correction des numéros de vente pour: {schema_name}")
        print(f"{'='*60}\n")
        
        updated = 0
        errors = 0
        
        sales = Sale.objects.all()
        
        for sale in sales:
            try:
                year_in_number = sale.sale_number[3:7]  # Extract VTEyyyy
                actual_year = str(sale.sale_date.year)
                
                if year_in_number != actual_year:
                    print(f"\n❌ Incohérence trouvée: {sale.sale_number} (date: {sale.sale_date})")
                    
                    with transaction.atomic():
                        # Générer un nouveau numéro avec la bonne année
                        old_number = sale.sale_number
                        
                        # Trouver le prochain numéro pour cette année
                        last_sale = Sale.objects.filter(
                            sale_date__year=sale.sale_date.year
                        ).exclude(id=sale.id).select_for_update().order_by('-sale_number').first()
                        
                        if last_sale and last_sale.sale_number.startswith(f'VTE{actual_year}'):
                            try:
                                last_number_str = last_sale.sale_number.replace('VTE', '').replace(actual_year, '')
                                last_number = int(last_number_str)
                            except (ValueError, AttributeError):
                                last_number = 0
                        else:
                            last_number = 0
                        
                        next_number = last_number + 1
                        new_number = f"VTE{actual_year}{next_number:06d}"
                        
                        sale.sale_number = new_number
                        sale.save()
                        
                        # Mettre à jour les mouvements
                        movements_updated = StockMovement.objects.filter(reference=old_number).update(reference=new_number)
                        
                        print(f"✅ {old_number} → {new_number}")
                        print(f"   {movements_updated} mouvement(s) mis à jour")
                        updated += 1
                        
            except Exception as e:
                print(f"❌ Erreur pour {sale.sale_number}: {e}")
                errors += 1
        
        print(f"\n{'='*60}")
        print(f"Résumé:")
        print(f"  - Ventes corrigées: {updated}")
        print(f"  - Erreurs: {errors}")
        print(f"{'='*60}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_sale_numbers.py <schema_name>")
        print("Exemple: python fix_sale_numbers.py agribio")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        print(f"Tenant trouvé: {tenant.name} ({schema_name})")
        fix_incorrect_sale_numbers(schema_name)
    except Company.DoesNotExist:
        print(f"❌ Erreur: Le tenant '{schema_name}' n'existe pas")
        sys.exit(1)
