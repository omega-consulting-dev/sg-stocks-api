#!/usr/bin/env python
"""
Script pour migrer les FieldConfiguration du schéma public vers chaque tenant.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from apps.tenants.models import Company

print("=" * 70)
print("Migration des FieldConfiguration du schéma public vers les tenants")
print("=" * 70)

# 1. Récupérer les configurations du schéma public
connection.set_schema_to_public()
from core.models import FieldConfiguration

public_configs = list(FieldConfiguration.objects.all().values(
    'form_name', 'field_name', 'field_label', 
    'is_visible', 'is_required', 'display_order'
))

print(f"\n✓ {len(public_configs)} configurations trouvées dans le schéma public")

if not public_configs:
    print("\n[ATTENTION]  Aucune configuration à migrer. Exécutez d'abord init_field_configs.py")
    exit(0)

# 2. Migrer vers chaque tenant
tenants = Company.objects.exclude(schema_name='public')
print(f"\n✓ {tenants.count()} tenants trouvés\n")

for tenant in tenants:
    print(f"Migration vers {tenant.name} (schema: {tenant.schema_name})...")
    
    # Basculer vers le schéma du tenant
    connection.set_schema(tenant.schema_name)
    
    # Supprimer les anciennes configs si elles existent
    FieldConfiguration.objects.all().delete()
    
    # Créer les nouvelles configs
    created_count = 0
    for config_data in public_configs:
        FieldConfiguration.objects.create(**config_data)
        created_count += 1
    
    print(f"  ✓ {created_count} configurations créées")

print("\n" + "=" * 70)
print("[OK] Migration terminée avec succès!")
print("=" * 70)

# Retour au schéma public
connection.set_schema_to_public()
