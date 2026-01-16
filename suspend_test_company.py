#!/usr/bin/env python
"""Script pour suspendre une entreprise de test."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.tenants.models import Company

print("[INFO] Recherche de l'entreprise SAKER...\n")

company = Company.objects.get(schema_name='saker')
print(f"[OK] Entreprise trouvée: {company.name}")
print(f"   Avant: is_active={company.is_active}, is_suspended={company.is_suspended}")

# Suspendre l'entreprise
company.is_suspended = True
company.suspension_reason = "Test de suspension manuelle"
company.save()

print(f"   Après: is_active={company.is_active}, is_suspended={company.is_suspended}")
print(f"\n[OK] Entreprise '{company.name}' suspendue avec succès!")
print("\n[NOTE] Rechargez la page AdminSgStock et sélectionnez le filtre 'Suspendu'")
