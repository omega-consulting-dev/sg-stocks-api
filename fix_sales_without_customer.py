import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.sales.models import Sale
from apps.customers.models import Customer
from apps.invoicing.models import Invoice

def fix_sales_without_customer():
    """Corriger toutes les ventes sans client et générer leurs factures."""
    
    # Récupérer tous les tenants sauf public
    tenants = Company.objects.all().exclude(schema_name='public')
    
    print(f"\n{'='*80}")
    print(f"Correction des ventes sans client dans tous les tenants")
    print(f"{'='*80}\n")
    
    for tenant in tenants:
        print(f"\n📋 Tenant: {tenant.name} ({tenant.schema_name})")
        print("-" * 80)
        
        with schema_context(tenant.schema_name):
            # Récupérer ou créer le client "No Name"
            no_name_customer, created = Customer.objects.get_or_create(
                customer_code='CLI00001',
                defaults={
                    'name': 'Client No Name',
                    'phone': '',
                    'email': '',
                    'address': 'N/A',
                    'city': 'N/A',
                    'country': 'Cameroun'
                }
            )
            
            if created:
                print(f"  ✅ Client 'No Name' créé (Code: {no_name_customer.customer_code})")
            else:
                print(f"  ℹ️  Client 'No Name' existant (Code: {no_name_customer.customer_code})")
            
            # Récupérer toutes les ventes sans client
            sales_without_customer = Sale.objects.filter(customer__isnull=True)
            
            if not sales_without_customer.exists():
                print(f"  ℹ️  Aucune vente sans client")
                continue
            
            print(f"  📦 {sales_without_customer.count()} vente(s) sans client trouvée(s)")
            
            fixed_count = 0
            invoice_created_count = 0
            
            for sale in sales_without_customer:
                # Assigner le client No Name
                sale.customer = no_name_customer
                sale.save()
                fixed_count += 1
                
                # Vérifier si la vente est confirmée et n'a pas de facture
                if sale.status in ['confirmed', 'completed']:
                    try:
                        # Vérifier si une facture existe déjà
                        if hasattr(sale, 'invoice') and sale.invoice:
                            print(f"    {sale.sale_number}: Client assigné, facture déjà existante")
                        else:
                            # Générer la facture
                            invoice = Invoice.generate_from_sale(sale)
                            if invoice:
                                print(f"    {sale.sale_number}: Client assigné ✅ + Facture {invoice.invoice_number} créée ✅")
                                invoice_created_count += 1
                            else:
                                print(f"    {sale.sale_number}: Client assigné ✅ (facture non générée)")
                    except Exception as e:
                        print(f"    {sale.sale_number}: Client assigné ✅ (erreur facture: {str(e)})")
                else:
                    print(f"    {sale.sale_number}: Client assigné ✅ (statut: {sale.status})")
            
            print(f"\n  Résultat:")
            print(f"    - Ventes corrigées: {fixed_count}")
            print(f"    - Factures créées: {invoice_created_count}")
    
    print(f"\n{'='*80}")
    print(f"✅ Correction terminée pour tous les tenants")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    fix_sales_without_customer()
