#!/usr/bin/env python
"""
Supprimer l'enregistrement de migration de core et ré-appliquer
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model

print("\n" + "=" * 70)
print("Suppression des enregistrements de migration de core")
print("=" * 70)

# Pour chaque tenant (pas public car core n'est plus dans SHARED_APPS)
Tenant = get_tenant_model()
tenants = Tenant.objects.exclude(schema_name='public').all()

for tenant in tenants:
    connection.set_tenant(tenant)
    print(f"\n[PACKAGE] Tenant: {tenant.schema_name.upper()}")
    
    with connection.cursor() as cursor:
        # Supprimer les enregistrements de migration pour core
        cursor.execute("""
            DELETE FROM django_migrations 
            WHERE app = 'core';
        """)
        deleted = cursor.rowcount
        print(f"  ✓ {deleted} enregistrement(s) de migration supprimé(s)")

print("\n" + "=" * 70)
print("[OK] Terminé! Vous pouvez maintenant exécuter:")
print("   python manage.py migrate_schemas")
print("=" * 70)
