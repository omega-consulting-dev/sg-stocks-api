import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.invoicing.models import Invoice

def check_invoice(schema_name):
    """Vérifier si la facture ID 11 existe et lister toutes les factures."""
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        print(f"Tenant trouvé: {tenant.name} ({tenant.schema_name})\n")
    except Company.DoesNotExist:
        print(f"❌ Tenant '{schema_name}' non trouvé")
        return
    
    with schema_context(schema_name):
        print(f"{'='*60}")
        print(f"Vérification facture ID 11")
        print(f"{'='*60}\n")
        
        # Vérifier facture ID 11
        try:
            invoice_11 = Invoice.objects.get(id=11)
            print(f"✅ Facture ID 11 existe:")
            print(f"   Numéro: {invoice_11.invoice_number}")
            print(f"   Client: {invoice_11.customer.name}")
            print(f"   Date: {invoice_11.invoice_date}")
            print(f"   Montant: {invoice_11.total_amount}")
            print(f"   Statut: {invoice_11.status}")
            print(f"   Lignes: {invoice_11.lines.count()}")
        except Invoice.DoesNotExist:
            print(f"❌ Facture ID 11 n'existe PAS\n")
        
        # Lister toutes les factures
        print(f"\n{'='*60}")
        print(f"Liste de toutes les factures:")
        print(f"{'='*60}\n")
        
        invoices = Invoice.objects.all().order_by('id')
        for inv in invoices:
            lines_count = inv.lines.count()
            print(f"ID {inv.id:3d} | {inv.invoice_number:15s} | {inv.invoice_date} | "
                  f"{inv.customer.name:20s} | {inv.total_amount:10.2f} | "
                  f"{lines_count} ligne(s)")
        
        print(f"\nTotal: {invoices.count()} facture(s)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_invoice_11.py <schema_name>")
        sys.exit(1)
    
    check_invoice(sys.argv[1])
