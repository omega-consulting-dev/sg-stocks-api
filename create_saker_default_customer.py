import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.customers.models import Customer
from apps.sales.models import Sale
from apps.invoicing.models import Invoice

with schema_context('saker'):
    print("Création d'un client par défaut dans Saker...\n")
    
    # Vérifier s'il existe déjà
    customer = Customer.objects.filter(name__icontains='Client No Name').first()
    
    if not customer:
        # Créer le client
        count = Customer.objects.count() + 1
        customer = Customer.objects.create(
            name='Client No Name',
            customer_code=f'CLI{count:05d}',
            phone='',
            email='',
            city='',
            country='Cameroun'
        )
        print(f"✅ Client créé: {customer.name} ({customer.customer_code})")
    else:
        print(f"✅ Client trouvé: {customer.name} ({customer.customer_code})")
    
    # Assigner le client à la vente sans client
    sales_without_customer = Sale.objects.filter(customer__isnull=True)
    
    if sales_without_customer.exists():
        print(f"\n{sales_without_customer.count()} vente(s) sans client trouvée(s)\n")
        
        for sale in sales_without_customer:
            print(f"  Vente {sale.sale_number}:")
            sale.customer = customer
            sale.save()
            print(f"    ✅ Client assigné")
            
            # Si la vente est confirmée, créer la facture
            if sale.status in ['confirmed', 'completed']:
                try:
                    invoice = Invoice.generate_from_sale(sale)
                    print(f"    ✅ Facture {invoice.invoice_number} créée (ID: {invoice.id})")
                except Exception as e:
                    print(f"    ❌ Erreur facture: {str(e)}")
    else:
        print("\nAucune vente sans client")
    
    print(f"\n{'='*80}")
    print("Terminé!")
