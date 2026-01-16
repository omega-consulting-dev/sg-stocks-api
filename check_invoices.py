"""
Script pour vérifier les factures dans un tenant.
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import tenant_context
from apps.tenants.models import Company
from apps.invoicing.models import Invoice

def check_invoices(tenant_schema_name):
    try:
        tenant = Company.objects.get(schema_name=tenant_schema_name)
        print(f"\n{'='*60}")
        print(f"FACTURES - TENANT: {tenant.name}")
        print(f"{'='*60}\n")
        
        with tenant_context(tenant):
            invoices = Invoice.objects.all().order_by('-created_at')
            
            if invoices.count() == 0:
                print("❌ Aucune facture trouvée")
                return
            
            print(f"✅ {invoices.count()} facture(s) trouvée(s)\n")
            
            for inv in invoices:
                print(f"📄 Facture #{inv.id} - {inv.invoice_number}")
                print(f"   Date: {inv.invoice_date}")
                print(f"   Store: {inv.store.name} (ID: {inv.store.id})")
                print(f"   Client: {inv.customer.name if inv.customer else 'Aucun'}")
                print(f"   Montant total: {inv.total_amount} FCFA")
                print(f"   Créé le: {inv.created_at}")
                print(f"   Lignes:")
                for line in inv.lines.all():
                    print(f"      - {line.product.name if hasattr(line, 'product') and line.product else line.description}: {line.quantity} x {line.unit_price} = {line.total}")
                print()
                
    except Company.DoesNotExist:
        print(f"❌ Le tenant '{tenant_schema_name}' n'existe pas.")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    tenant_name = 'agribio' if len(sys.argv) <= 1 else sys.argv[1]
    check_invoices(tenant_name)
