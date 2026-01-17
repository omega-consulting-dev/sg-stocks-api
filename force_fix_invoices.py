import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')

django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company
from apps.invoicing.models import Invoice
from apps.inventory.models import StockMovement
from django.db import transaction

def force_fix_all_invoices(schema_name):
    """
    Force la correction de toutes les factures dont le numéro ne correspond pas à l'année
    Utilise un renommage en deux passes pour éviter les conflits
    """
    with schema_context(schema_name):
        print(f"\n{'='*60}")
        print(f"Force correction de toutes les factures pour: {schema_name}")
        print(f"{'='*60}\n")
        
        # Grouper les factures par année
        invoices_by_year = {}
        for invoice in Invoice.objects.all().order_by('invoice_date'):
            year = invoice.invoice_date.year
            if year not in invoices_by_year:
                invoices_by_year[year] = []
            invoices_by_year[year].append(invoice)
        
        updated = 0
        errors = 0
        
        # Pour chaque année, regénérer les numéros dans l'ordre chronologique
        for year in sorted(invoices_by_year.keys()):
            invoices = invoices_by_year[year]
            print(f"\nAnnée {year}: {len(invoices)} facture(s)")
            print("-" * 40)
            
            # Première passe: renommer en temporaire
            temp_numbers = {}
            for index, invoice in enumerate(invoices, start=1):
                temp_number = f"TEMP_{year}_{index:06d}"
                old_number = invoice.invoice_number
                
                try:
                    with transaction.atomic():
                        invoice.invoice_number = temp_number
                        invoice.save()
                        temp_numbers[temp_number] = (old_number, index)
                except Exception as e:
                    print(f"❌ Erreur renommage temp pour {old_number}: {e}")
                    errors += 1
            
            # Deuxième passe: renommer avec les vrais numéros
            for temp_number, (old_number, index) in temp_numbers.items():
                new_number = f"FAC{year}{index:06d}"
                
                try:
                    with transaction.atomic():
                        invoice = Invoice.objects.get(invoice_number=temp_number)
                        invoice.invoice_number = new_number
                        invoice.save()
                        
                        # Mettre à jour les mouvements
                        old_ref = f"FACT-{old_number}"
                        new_ref = f"FACT-{new_number}"
                        movements_updated = StockMovement.objects.filter(reference=old_ref).update(reference=new_ref)
                        
                        if old_number != new_number:
                            print(f"✅ {old_number} → {new_number} ({movements_updated} mvts)")
                            updated += 1
                        else:
                            print(f"✓  {new_number} - Déjà correct")
                except Exception as e:
                    print(f"❌ Erreur pour {temp_number}: {e}")
                    errors += 1
        
        print(f"\n{'='*60}")
        print(f"Résumé:")
        print(f"  - Factures corrigées: {updated}")
        print(f"  - Erreurs: {errors}")
        print(f"{'='*60}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python force_fix_invoices.py <schema_name>")
        print("Exemple: python force_fix_invoices.py agribio")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        print(f"Tenant trouvé: {tenant.name} ({schema_name})")
        force_fix_all_invoices(schema_name)
    except Company.DoesNotExist:
        print(f"❌ Erreur: Le tenant '{schema_name}' n'existe pas")
        sys.exit(1)
