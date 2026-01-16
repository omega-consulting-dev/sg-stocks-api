import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from apps.inventory.models import StockTransfer, StockMovement, Store, Stock
from apps.accounts.models import User
from django_tenants.utils import schema_context
from apps.tenants.models import Company

tenant = Company.objects.get(schema_name='santa')

with schema_context(tenant.schema_name):
    print("=== UTILISATEURS DU TENANT SANTA ===\n")
    
    users = User.objects.all()
    for user in users:
        print(f"Utilisateur: {user.username} ({user.email})")
        if user.role:
            print(f"  Role: {user.role}")
            print(f"  Role.name: '{user.role.name}'")
            print(f"  Role.can_manage_inventory: {user.role.can_manage_inventory}")
            print(f"  Role.access_scope: {user.role.access_scope}")
        else:
            print(f"  Role: None")
        print(f"  is_superuser: {user.is_superuser}")
        print(f"  Magasins assignés: {[s.name for s in user.assigned_stores.all()]}")
        print()
    
    print("\n=== MAGASINS ===\n")
    stores = Store.objects.all()
    for store in stores:
        print(f"{store.name} (ID: {store.id})")
        print(f"  Code: {store.code}")
        print(f"  Manager: {store.manager}")
        print()
    
    print("\n=== STOCKS DANS MAGASIN DOUALA ===\n")
    douala = Store.objects.get(name="Magasin Douala")
    stocks = Stock.objects.filter(store=douala).select_related('product')
    for stock in stocks:
        print(f"{stock.product.name}: {stock.quantity}")
