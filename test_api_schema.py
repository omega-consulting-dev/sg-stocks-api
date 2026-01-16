#!/usr/bin/env python
"""
Test pour vérifier quel schéma est utilisé par l'API
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from apps.tenants.models import Company

print("\n" + "=" * 70)
print("Test: Quel schéma utilise l'API actuellement?")
print("=" * 70)

# Simuler ce que fait l'API
print(f"\nSchéma actuel: {connection.schema_name}")

# Basculer vers agribio
tenant = Company.objects.get(schema_name='agribio')
connection.set_tenant(tenant)
print(f"Après set_tenant(agribio): {connection.schema_name}")

from core.models import FieldConfiguration
count = FieldConfiguration.objects.count()
print(f"Nombre de configs dans agribio: {count}")

# Test sur saker
tenant = Company.objects.get(schema_name='saker')
connection.set_tenant(tenant)
print(f"\nAprès set_tenant(saker): {connection.schema_name}")
count = FieldConfiguration.objects.count()
print(f"Nombre de configs dans saker: {count}")

print("\n" + "=" * 70)
