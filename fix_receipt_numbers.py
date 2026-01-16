#!/usr/bin/env python
"""
Mettre à jour les achats sans receipt_number
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model
from apps.inventory.models import StockMovement

print("\n" + "=" * 70)
print("Mise à jour des achats sans receipt_number")
print("=" * 70)

Tenant = get_tenant_model()
tenants = Tenant.objects.exclude(schema_name='public').all()

for tenant in tenants:
    connection.set_tenant(tenant)
    print(f"\n[PACKAGE] Tenant: {tenant.schema_name.upper()}")
    
    # Trouver les mouvements d'entrée sans receipt_number
    movements_without_receipt = StockMovement.objects.filter(
        movement_type='in',
        receipt_number__isnull=True
    ).order_by('created_at')
    
    count = movements_without_receipt.count()
    if count == 0:
        print(f"  ✓ Aucun mouvement sans receipt_number")
        continue
    
    print(f"  [ATTENTION]  {count} mouvement(s) sans receipt_number trouvé(s)")
    
    # Trouver le dernier numéro de reçu existant
    last_receipt = StockMovement.objects.filter(
        movement_type='in',
        receipt_number__startswith='RECEIPT-'
    ).order_by('receipt_number').values_list('receipt_number', flat=True).last()
    
    if last_receipt:
        last_num = int(last_receipt.split('-')[1])
    else:
        last_num = 0
    
    print(f"  [NOTE] Dernier numéro de reçu: {last_receipt or 'Aucun'}")
    
    # Assigner des numéros de reçu aux mouvements
    updated = 0
    for movement in movements_without_receipt:
        last_num += 1
        new_receipt = f"RECEIPT-{str(last_num).zfill(3)}"
        movement.receipt_number = new_receipt
        movement.save()
        updated += 1
        print(f"    ✓ Mouvement #{movement.id} -> {new_receipt}")
    
    print(f"  [OK] {updated} mouvement(s) mis à jour")

print("\n" + "=" * 70)
print("[OK] Terminé! Tous les mouvements ont maintenant un receipt_number")
print("=" * 70)
