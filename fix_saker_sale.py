import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.sales.models import Sale
from apps.customers.models import Customer
from apps.invoicing.models import Invoice

with schema_context('saker'):
    print("Vérification de la vente VTE2026000001:\n")
    
    sale = Sale.objects.get(sale_number='VTE2026000001')
    
    print(f"Numéro: {sale.sale_number}")
    print(f"Date: {sale.sale_date}")
    print(f"Client: {sale.customer}")
    print(f"Montant: {sale.total_amount} FCFA")
    print(f"Statut: {sale.status}")
    print(f"Lignes: {sale.lines.count()}")
    
    if sale.lines.exists():
        print("\nLignes de vente:")
        for line in sale.lines.all():
            print(f"  - {line.description}: {line.quantity} x {line.unit_price} FCFA")
    
    if not sale.customer:
        print("\n❌ Cette vente n'a pas de client!")
        print("\nClients disponibles:")
        customers = Customer.objects.all()
        for i, customer in enumerate(customers, 1):
            print(f"  {i}. {customer.name} ({customer.customer_code})")
        
        if customers.exists():
            choice = input("\nAssigner à quel client? (numéro ou 'n' pour annuler): ")
            if choice.lower() != 'n':
                try:
                    customer = list(customers)[int(choice) - 1]
                    sale.customer = customer
                    sale.save()
                    print(f"\n✅ Client {customer.name} assigné à la vente")
                    
                    # Tenter de créer la facture
                    print("\nCréation de la facture...")
                    invoice = Invoice.generate_from_sale(sale)
                    if invoice:
                        print(f"✅ Facture {invoice.invoice_number} créée (ID: {invoice.id})")
                    else:
                        print("❌ Erreur lors de la création de la facture")
                except Exception as e:
                    print(f"❌ Erreur: {str(e)}")
