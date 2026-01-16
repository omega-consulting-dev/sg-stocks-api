import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from apps.inventory.models import StockTransfer, Stock, StockMovement
from django_tenants.utils import schema_context
from apps.tenants.models import Company

tenant = Company.objects.get(schema_name='santa')

with schema_context(tenant.schema_name):
    # Dernier transfert
    t = StockTransfer.objects.order_by('-created_at').first()
    print(f"Transfert: {t.transfer_number} - Status: {t.status}")
    print(f"Source: {t.source_store.name} -> Destination: {t.destination_store.name}")
    print()
    
    # Vérifier les stocks source
    for line in t.lines.all():
        try:
            stock = Stock.objects.get(
                product=line.product,
                store=t.source_store
            )
            print(f"Produit: {line.product.name}")
            print(f"  - Quantité demandée: {line.quantity_requested}")
            print(f"  - Stock disponible: {stock.quantity}")
            print(f"  - Stock réservé: {stock.reserved_quantity}")
            print(f"  - Stock dispo pour transfert: {stock.quantity - stock.reserved_quantity}")
            
            if line.quantity_requested > (stock.quantity - stock.reserved_quantity):
                print(f"  [ATTENTION] PROBLÈME: Quantité demandée supérieure au stock disponible!")
            else:
                print(f"  [OK] OK")
        except Stock.DoesNotExist:
            print(f"Produit: {line.product.name}")
            print(f"  [ERREUR] ERREUR: Aucun stock trouvé dans le magasin source!")
        print()
