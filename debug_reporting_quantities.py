"""Script pour déboguer les quantités dans le reporting."""
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.settings.local')
django.setup()

from apps.invoicing.models import Invoice, InvoicePayment
from apps.sales.models import Sale

# Date de test - toutes les données
start_date = datetime(2020, 1, 1).date()
end_date = datetime(2030, 12, 31).date()

print("=" * 80)
print("DEBUG REPORTING - QUANTITÉS")
print("=" * 80)

# 1. Vérifier les paiements de factures
invoice_payments = InvoicePayment.objects.filter(
    payment_date__gte=start_date,
    payment_date__lte=end_date,
    status='success'
).select_related('invoice')

print(f"\n📊 Total paiements de factures: {invoice_payments.count()}")

for payment in invoice_payments[:3]:  # Juste les 3 premiers
    print(f"\n💳 Paiement: {payment.id} - Montant: {payment.amount}")
    print(f"   Facture: {payment.invoice.invoice_number}")
    print(f"   Total facture: {payment.invoice.total_amount}")
    
    if hasattr(payment.invoice, 'lines'):
        print(f"   Lignes de facture:")
        for line in payment.invoice.lines.all():
            category = 'N/A'
            if hasattr(line, 'product') and line.product:
                if hasattr(line.product, 'category') and line.product.category:
                    category = line.product.category.name
            elif hasattr(line, 'service') and line.service:
                if hasattr(line.service, 'category') and line.service.category:
                    category = line.service.category.name
            
            quantity = float(line.quantity) if hasattr(line, 'quantity') else 0
            total = float(line.total) if hasattr(line, 'total') else 0
            
            print(f"      - Catégorie: {category}")
            print(f"        Quantité: {quantity}")
            print(f"        Total ligne: {total}")

# 2. Vérifier les ventes directes
sales = Sale.objects.filter(
    sale_date__gte=start_date,
    sale_date__lte=end_date,
    status__in=['confirmed', 'completed'],
    paid_amount__gt=0
)

print(f"\n\n📦 Total ventes directes: {sales.count()}")

for sale in sales[:3]:  # Juste les 3 premières
    print(f"\n🛒 Vente: {sale.sale_number} - Payé: {sale.paid_amount}/{sale.total_amount}")
    
    if hasattr(sale, 'lines'):
        print(f"   Lignes de vente:")
        for line in sale.lines.all():
            category = 'N/A'
            if hasattr(line, 'product') and line.product:
                if hasattr(line.product, 'category') and line.product.category:
                    category = line.product.category.name
            elif hasattr(line, 'service') and line.service:
                if hasattr(line.service, 'category') and line.service.category:
                    category = line.service.category.name
            
            quantity = float(line.quantity) if hasattr(line, 'quantity') else 0
            unit_price = float(line.unit_price) if hasattr(line, 'unit_price') else 0
            
            print(f"      - Catégorie: {category}")
            print(f"        Quantité: {quantity}")
            print(f"        Prix unitaire: {unit_price}")
            print(f"        Total: {quantity * unit_price}")

print("\n" + "=" * 80)
