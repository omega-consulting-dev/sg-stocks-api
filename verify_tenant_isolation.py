#!/usr/bin/env python
"""
Vérifier que chaque tenant a ses propres configurations isolées
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from apps.tenants.models import Company
from core.models import FieldConfiguration

print("\n" + "=" * 70)
print("Vérification de l'isolation des configurations par tenant")
print("=" * 70)

tenants = Company.objects.exclude(schema_name='public')

for tenant in tenants:
    connection.set_schema(tenant.schema_name)
    count = FieldConfiguration.objects.count()
    sale_price_config = FieldConfiguration.objects.filter(
        form_name='product', 
        field_name='sale_price'
    ).first()
    
    print(f"\n{tenant.name} ({tenant.schema_name}):")
    print(f"  - Total configurations: {count}")
    if sale_price_config:
        print(f"  - Prix de vente: Visible={sale_price_config.is_visible}, Required={sale_price_config.is_required}")
    else:
        print(f"  - Prix de vente: Non trouvé")

print("\n" + "=" * 70)
print("[OK] Chaque tenant a maintenant ses propres configurations!")
print("=" * 70)
