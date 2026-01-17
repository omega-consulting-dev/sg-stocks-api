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

def check_sale_invoice(schema_name):
    """Vérifier la facture liée à la vente VTE2025000008."""
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        print(f"Tenant trouvé: {tenant.name} ({tenant.schema_name})\n")
    except Company.DoesNotExist:
        print(f"❌ Tenant '{schema_name}' non trouvé")
        return
    
    with schema_context(schema_name):
        print(f"{'='*70}")
        print(f"Recherche de la vente VTE2025000008")
        print(f"{'='*70}\n")
        
        # Chercher la vente
        try:
            sale = Sale.objects.get(sale_number='VTE2025000008')
            print(f"✅ Vente trouvée:")
            print(f"   ID: {sale.id}")
            print(f"   Numéro: {sale.sale_number}")
            print(f"   Date: {sale.sale_date}")
            print(f"   Client: {sale.customer.name}")
            print(f"   Montant: {sale.total_amount}")
            print(f"   Statut: {sale.status}")
            
            # Chercher la facture liée
            if hasattr(sale, 'invoice') and sale.invoice:
                invoice = sale.invoice
                print(f"\n✅ Facture liée trouvée:")
                print(f"   ID: {invoice.id}")
                print(f"   Numéro: {invoice.invoice_number}")
                print(f"   Date: {invoice.invoice_date}")
                print(f"   Montant: {invoice.total_amount}")
                print(f"   Lignes: {invoice.lines.count()}")
            else:
                print(f"\n❌ Aucune facture liée à cette vente")
                
        except Sale.DoesNotExist:
            print(f"❌ Vente VTE2025000008 non trouvée\n")
        
        # Lister toutes les ventes
        print(f"\n{'='*70}")
        print(f"Liste de toutes les ventes:")
        print(f"{'='*70}\n")
        
        sales = Sale.objects.all().order_by('id')
        for s in sales:
            invoice_info = ""
            if hasattr(s, 'invoice') and s.invoice:
                invoice_info = f" → Facture ID {s.invoice.id} ({s.invoice.invoice_number})"
            else:
                invoice_info = " → Pas de facture"
            print(f"ID {s.id:3d} | {s.sale_number:15s} | {s.sale_date} | "
                  f"{s.customer.name:20s}{invoice_info}")
        
        print(f"\nTotal: {sales.count()} vente(s)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_sale_invoice.py <schema_name>")
        sys.exit(1)
    
    check_sale_invoice(sys.argv[1])
