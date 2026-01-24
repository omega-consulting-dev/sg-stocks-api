import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from apps.invoicing.models import Invoice, InvoicePayment
from apps.sales.models import Sale
from django.db.models import Q

# Récupérer les paiements de factures avec succès
print("=" * 80)
print("ANALYSE DES QUANTITÉS DANS LES FACTURES")
print("=" * 80)

invoice_payments = InvoicePayment.objects.filter(status='success').select_related('invoice')[:3]

for payment in invoice_payments:
    print(f"\n=== Facture #{payment.invoice.invoice_number} - Montant payé: {payment.amount:,.0f} ===")
    if hasattr(payment.invoice, 'lines'):
        total_quantity = 0
        for line in payment.invoice.lines.all():
            product_name = line.product.name if line.product else (line.service.name if line.service else 'N/A')
            category = line.product.category.name if (line.product and line.product.category) else (line.service.category.name if (line.service and line.service.category) else 'N/A')
            print(f"  - {product_name}")
            print(f"    Catégorie: {category}")
            print(f"    Quantité: {line.quantity}")
            print(f"    Prix unitaire: {line.unit_price:,.0f}")
            print(f"    Total ligne: {line.total:,.0f}")
            total_quantity += line.quantity
        print(f"  TOTAL QUANTITÉ FACTURE: {total_quantity}")
        print(f"  Total facture: {payment.invoice.total_amount:,.0f}")

print("\n" + "=" * 80)
print("ANALYSE DES QUANTITÉS DANS LES VENTES DIRECTES")
print("=" * 80)

sales = Sale.objects.filter(
    status__in=['confirmed', 'completed'],
    paid_amount__gt=0
).prefetch_related('lines')[:3]

for sale in sales:
    print(f"\n=== Vente #{sale.sale_number} - Montant payé: {sale.paid_amount:,.0f} ===")
    if hasattr(sale, 'lines'):
        total_quantity = 0
        for line in sale.lines.all():
            product_name = line.product.name if line.product else (line.service.name if line.service else 'N/A')
            category = line.product.category.name if (line.product and line.product.category) else (line.service.category.name if (line.service and line.service.category) else 'N/A')
            print(f"  - {product_name}")
            print(f"    Catégorie: {category}")
            print(f"    Quantité: {line.quantity}")
            print(f"    Prix unitaire: {line.unit_price:,.0f}")
            line_total = line.quantity * line.unit_price
            print(f"    Total ligne: {line_total:,.0f}")
            total_quantity += line.quantity
        print(f"  TOTAL QUANTITÉ VENTE: {total_quantity}")
        print(f"  Total vente: {sale.total_amount:,.0f}")
