#!/usr/bin/env python
"""Script pour vérifier le statut de toutes les entreprises."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.tenants.models import Company

print("[INFO] Vérification du statut des entreprises\n")
print("=" * 60)

companies = Company.objects.all()
print(f"\n[STATS] Total: {companies.count()} entreprise(s)\n")

for c in companies:
    status = []
    if c.is_active:
        status.append("[OK] ACTIVE")
    else:
        status.append("[ERREUR] INACTIVE")
    
    if c.is_suspended:
        status.append("🔴 SUSPENDUE")
        status.append(f"Raison: {c.suspension_reason or 'Non spécifiée'}")
    
    print(f"ID: {c.id}")
    print(f"Nom: {c.name}")
    print(f"Schema: {c.schema_name}")
    print(f"Status: {' | '.join(status)}")
    print(f"is_active: {c.is_active}")
    print(f"is_suspended: {c.is_suspended}")
    print("-" * 60)
