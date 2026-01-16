#!/usr/bin/env python
"""
Vérifier dans quel schéma existe la table core_fieldconfiguration
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model

print("\n" + "=" * 70)
print("Vérification de l'existence de core_fieldconfiguration")
print("=" * 70)

# Vérifier dans public
connection.set_schema_to_public()
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'core_fieldconfiguration'
        );
    """)
    exists_public = cursor.fetchone()[0]
    print(f"\n[PACKAGE] PUBLIC: {'✓ Table existe' if exists_public else '✗ Table n\'existe PAS'}")

# Vérifier dans chaque tenant
Tenant = get_tenant_model()
tenants = Tenant.objects.exclude(schema_name='public').all()

for tenant in tenants:
    connection.set_tenant(tenant)
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = '{tenant.schema_name}' 
                AND table_name = 'core_fieldconfiguration'
            );
        """)
        exists = cursor.fetchone()[0]
        
        # Compter les enregistrements si la table existe
        count = 0
        if exists:
            cursor.execute("SELECT COUNT(*) FROM core_fieldconfiguration;")
            count = cursor.fetchone()[0]
        
        status = f"✓ Table existe ({count} configs)" if exists else "✗ Table n'existe PAS"
        print(f"[PACKAGE] {tenant.schema_name.upper()}: {status}")

print("\n" + "=" * 70)
