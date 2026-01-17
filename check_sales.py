import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.sales.models import Sale

def check_sales(schema_name):
    """Vérifier toutes les ventes"""
    with schema_context(schema_name):
        print(f"\n{'='*60}")
        print(f"Liste des ventes pour: {schema_name}")
        print(f"{'='*60}\n")
        
        sales = Sale.objects.all().order_by('sale_date')
        
        for sale in sales:
            year_in_number = sale.sale_number[3:7]  # Extract year from VTEyyyy
            actual_year = str(sale.sale_date.year)
            
            match = "✅" if year_in_number == actual_year else "❌"
            print(f"{match} {sale.sale_number} | Date: {sale.sale_date} | Year: {actual_year}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_sales.py <schema_name>")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        check_sales(schema_name)
    except Company.DoesNotExist:
        print(f"❌ Erreur: Le tenant '{schema_name}' n'existe pas")
        sys.exit(1)
