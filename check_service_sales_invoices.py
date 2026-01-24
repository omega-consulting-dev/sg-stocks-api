import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.invoicing.models import Invoice
from apps.sales.models import Sale

def check_service_sales():
    """Vérifier les ventes de services et leurs factures."""
    
    # Demander le tenant
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
        # Récupérer toutes les ventes de services confirmées
        service_sales = Sale.objects.filter(
            lines__line_type='service',
            status__in=['confirmed', 'completed']
        ).distinct().order_by('-sale_date')
        
        print(f"Total ventes de services confirmées: {service_sales.count()}\n")
        
        # Vérifier chaque vente
        sales_without_invoice = []
        sales_with_invoice = []
        
        for sale in service_sales:
            has_invoice = False
            invoice_info = ""
            
            try:
                if hasattr(sale, 'invoice') and sale.invoice:
                    has_invoice = True
                    invoice_info = f"Facture: {sale.invoice.invoice_number} (ID: {sale.invoice.id})"
                    sales_with_invoice.append(sale)
            except Exception as e:
                pass
            
            if not has_invoice:
                invoice_info = "❌ PAS DE FACTURE"
                sales_without_invoice.append(sale)
            
            customer_name = sale.customer.name if sale.customer else "N/A"
            print(f"  {sale.sale_number} | {sale.sale_date} | {customer_name:20s} | "
                  f"{sale.total_amount:>10} FCFA | {sale.status:10s} | {invoice_info}")
        
        print(f"\n{'='*80}")
        print(f"Résumé:")
        print(f"  ✅ Ventes avec facture: {len(sales_with_invoice)}")
        print(f"  ❌ Ventes SANS facture: {len(sales_without_invoice)}")
        print(f"{'='*80}")
        
        if sales_without_invoice:
            print(f"\n⚠️  Ventes sans facture:")
            for sale in sales_without_invoice:
                customer_name = sale.customer.name if sale.customer else "N/A"
                print(f"  - {sale.sale_number} | {customer_name} | {sale.total_amount} FCFA | {sale.sale_date}")
            
            create_choice = input(f"\nVoulez-vous créer les factures manquantes pour ces {len(sales_without_invoice)} ventes? (o/n): ")
            if create_choice.lower() == 'o':
                create_missing_invoices(tenant.schema_name, sales_without_invoice)

def create_missing_invoices(schema_name, sales):
    """Créer les factures manquantes pour les ventes."""
    with schema_context(schema_name):
        created_count = 0
        failed_count = 0
        
        for sale in sales:
            try:
                print(f"\n  Création facture pour {sale.sale_number}...", end=" ")
                invoice = Invoice.generate_from_sale(sale)
                if invoice:
                    print(f"✅ Facture {invoice.invoice_number} créée (ID: {invoice.id})")
                    created_count += 1
                else:
                    print(f"❌ Échec (aucune facture retournée)")
                    failed_count += 1
            except Exception as e:
                print(f"❌ Erreur: {str(e)}")
                failed_count += 1
        
        print(f"\n{'='*80}")
        print(f"Résultat:")
        print(f"  ✅ Factures créées: {created_count}")
        print(f"  ❌ Échecs: {failed_count}")
        print(f"{'='*80}")

if __name__ == '__main__':
    check_service_sales()
