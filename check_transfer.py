import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from apps.inventory.models import StockTransfer, StockMovement
from django_tenants.utils import schema_context
from apps.tenants.models import Company

tenant = Company.objects.get(schema_name='santa')

with schema_context(tenant.schema_name):
    # Les 3 derniers transferts
    transfers = StockTransfer.objects.order_by('-created_at')[:3]
    
    for t in transfers:
        print(f"\nTransfert {t.transfer_number}:")
        print(f"  ID: {t.id}")
        print(f"  Status: {t.status}")
        print(f"  Créé le: {t.created_at}")
        print(f"  Source: {t.source_store.name}")
        print(f"  Destination: {t.destination_store.name}")
        
        # StockMovements liés
        movements = StockMovement.objects.filter(reference=t.transfer_number)
        print(f"  StockMovements: {movements.count()}")
        
        print(f"  Lignes:")
        for line in t.lines.all():
            print(f"    - {line.product.name}: demandé={line.quantity_requested}, envoyé={line.quantity_sent}")
    
    if not transfers:
        print("Aucun transfert trouvé")
