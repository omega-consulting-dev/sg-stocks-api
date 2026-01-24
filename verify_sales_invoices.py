import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.sales.models import Sale

def verify_sales_invoices():
    """Vérifier que les ventes ont bien leurs factures associées."""
    
    print("Tenants disponibles:")
    tenants = Company.objects.all().exclude(schema_name='public')
    for i, tenant in enumerate(tenants, 1):
        print(f"  {i}. {tenant.name} ({tenant.schema_name})")
    
    choice = input("\nSélectionnez un tenant (numéro): ")
    try:
        tenant = list(tenants)[int(choice) - 1]
    except (ValueError, IndexError):
        print("❌ Choix invalide")
        return
    
    print(f"\n{'='*80}")
    print(f"Tenant: {tenant.name} ({tenant.schema_name})")
    print(f"{'='*80}\n")
    
    with schema_context(tenant.schema_name):
        # Récupérer toutes les ventes de services
        service_sales = Sale.objects.filter(
            lines__line_type='service',
            status__in=['confirmed', 'completed']
        ).distinct().order_by('-sale_date')
        
        print(f"Vérification de {service_sales.count()} ventes de services:\n")
        
        for sale in service_sales:
            # Rafraîchir depuis la base de données
            sale.refresh_from_db()
            
            invoice_info = "❌ PAS DE FACTURE"
            invoice_id = None
            
            try:
                if hasattr(sale, 'invoice') and sale.invoice:
                    invoice_info = f"✅ Facture {sale.invoice.invoice_number} (ID: {sale.invoice.id})"
                    invoice_id = sale.invoice.id
            except Exception as e:
                invoice_info = f"❌ Erreur: {str(e)}"
            
            customer_name = sale.customer.name if sale.customer else "N/A"
            print(f"{sale.sale_number:15s} | {customer_name:20s} | "
                  f"{str(sale.total_amount):>10s} FCFA | {invoice_info}")
        
        print(f"\n{'='*80}")

if __name__ == '__main__':
    verify_sales_invoices()
