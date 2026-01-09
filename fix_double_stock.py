import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.inventory.models import Stock
from apps.products.models import Product

with schema_context('agribio'):
    print("=" * 80)
    print("CORRECTION DES STOCKS (diviser par 2)")
    print("=" * 80)
    
    stocks = Stock.objects.all()
    
    for stock in stocks:
        old_qty = stock.quantity
        new_qty = old_qty / 2
        
        stock.quantity = new_qty
        stock.save()
        
        print(f"\n✅ {stock.product.name} ({stock.store.name})")
        print(f"   Ancienne quantité: {old_qty}")
        print(f"   Nouvelle quantité: {new_qty}")
    
    print("\n" + "=" * 80)
    print("✅ CORRECTION TERMINÉE")
    print("=" * 80)
