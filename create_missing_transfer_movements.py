#!/usr/bin/env python
"""
Créer rétroactivement les mouvements 'transfer' pour les transferts reçus.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.inventory.models import StockTransfer, StockMovement
from django.utils import timezone

# Spécifier le tenant (schéma)
TENANT_SCHEMA = 'dov'

print("\n" + "=" * 60)
print(f"CRÉATION RÉTROACTIVE : Mouvements 'transfer' (Tenant: {TENANT_SCHEMA})")
print("=" * 60)

# Exécuter dans le bon schéma
with schema_context(TENANT_SCHEMA):
    # Trouver tous les transferts reçus sans mouvement 'transfer' associé
    transferred = StockTransfer.objects.filter(status__in=['in_transit', 'received'])
    
    print(f"\n[STATS] Transferts trouvés: {transferred.count()}")
    
    created_count = 0
    
    for transfer in transferred:
        # Vérifier si un mouvement 'transfer' existe déjà pour ce transfert
        exists = StockMovement.objects.filter(
            reference=transfer.transfer_number,
            movement_type='transfer'
        ).exists()
        
        if exists:
            print(f"✓ Transfert {transfer.transfer_number} - Mouvement 'transfer' existe déjà")
        else:
            # Créer les mouvements 'transfer' pour chaque ligne
            for line in transfer.lines.all():
                quantity = line.quantity_sent or line.quantity_requested
                
                StockMovement.objects.create(
                    product=line.product,
                    store=transfer.source_store,
                    destination_store=transfer.destination_store,
                    movement_type='transfer',
                    quantity=quantity,
                    reference=transfer.transfer_number,
                    notes=f'Transfert vers {transfer.destination_store.name}',
                    date=transfer.transfer_date,
                    created_by=transfer.validated_by or transfer.created_by
                )
                created_count += 1
                print(f"✓ Transfert {transfer.transfer_number} - Mouvement 'transfer' créé pour {line.product.name} (Qté: {quantity})")
    
    print(f"\n[OK] Total mouvements 'transfer' créés: {created_count}")

print("\n" + "=" * 60)
