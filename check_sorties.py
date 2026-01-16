import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from apps.inventory.models import StockMovement
from django_tenants.utils import schema_context
from apps.tenants.models import Company

tenant = Company.objects.get(schema_name='santa')

with schema_context(tenant.schema_name):
    # Mouvements de type transfer ou out
    print("=== Mouvements de SORTIE (out + transfer) ===\n")
    
    sorties = StockMovement.objects.filter(
        movement_type__in=['out', 'transfer']
    ).order_by('-created_at')[:10]
    
    print(f"Total: {sorties.count()} mouvements\n")
    
    for m in sorties:
        print(f"Référence: {m.reference}")
        print(f"  Type: {m.get_movement_type_display()}")
        print(f"  Produit: {m.product.name}")
        print(f"  Quantité: {m.quantity}")
        print(f"  Magasin: {m.store.name}")
        if m.destination_store:
            print(f"  -> Destination: {m.destination_store.name}")
        print(f"  Date: {m.date}")
        print(f"  Créé le: {m.created_at}")
        print()
