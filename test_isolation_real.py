#!/usr/bin/env python
"""
Modifier une config dans agribio pour tester l'isolation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from apps.tenants.models import Company
from core.models import FieldConfiguration

print("\n" + "=" * 70)
print("Test: Modifier sale_price dans agribio uniquement")
print("=" * 70)

# 1. Modifier dans agribio
tenant = Company.objects.get(schema_name='agribio')
connection.set_tenant(tenant)

config = FieldConfiguration.objects.get(form_name='product', field_name='sale_price')
print(f"\nAGRIBIO - Avant: Visible={config.is_visible}, Required={config.is_required}")
config.is_visible = False
config.is_required = False
config.save()
print(f"AGRIBIO - Après: Visible={config.is_visible}, Required={config.is_required}")

# 2. Vérifier dans saker
tenant = Company.objects.get(schema_name='saker')
connection.set_tenant(tenant)

config = FieldConfiguration.objects.get(form_name='product', field_name='sale_price')
print(f"\nSAKER - État: Visible={config.is_visible}, Required={config.is_required}")

# 3. Vérifier dans demo
tenant = Company.objects.get(schema_name='demo')
connection.set_tenant(tenant)

config = FieldConfiguration.objects.get(form_name='product', field_name='sale_price')
print(f"DEMO - État: Visible={config.is_visible}, Required={config.is_required}")

print("\n" + "=" * 70)
print("Si saker et demo restent à True, l'isolation fonctionne!")
print("=" * 70)
