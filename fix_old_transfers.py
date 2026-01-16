#!/usr/bin/env python
"""
Script pour créer les StockMovement manquants pour les anciens transferts.
Les transferts qui ont été créés directement en 'in_transit' sans passer par la validation
n'ont pas de StockMovement associés, donc ils n'apparaissent pas dans les mouvements.

Utilisation:
    python manage.py shell < fix_old_transfers.py
    OU
    python manage.py shell
    >>> exec(open('fix_old_transfers.py').read())
"""

from django.db import transaction
from apps.inventory.models import StockTransfer, StockMovement, Stock
from django.contrib.auth import get_user_model

User = get_user_model()

def fix_transfers():
    """Créer les StockMovement manquants pour les anciens transferts."""
    
    print("=" * 80)
    print("CORRECTION DES ANCIENS TRANSFERTS")
    print("=" * 80)
    
    # Trouver tous les transferts validés (in_transit ou received) sans StockMovement
    transfers = StockTransfer.objects.filter(
        status__in=['in_transit', 'received']
    ).select_related('source_store', 'destination_store').prefetch_related('lines__product')
    
    print(f"\n✓ Trouvé {transfers.count()} transferts en transit ou reçus")
    
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    
    for transfer in transfers:
        # Vérifier si des StockMovement existent déjà pour ce transfert
        existing_movements = StockMovement.objects.filter(
            reference=transfer.transfer_number,
            movement_type='transfer'
        ).count()
        
        if existing_movements > 0:
            print(f"  ⊘ Transfer {transfer.transfer_number}: StockMovement déjà existants ({existing_movements})")
            skipped_count += 1
            continue
        
        print(f"\n  -> Traitement du transfert {transfer.transfer_number}...")
        print(f"     Source: {transfer.source_store.name}")
        print(f"     Destination: {transfer.destination_store.name}")
        print(f"     Status: {transfer.status}")
        print(f"     Date: {transfer.transfer_date}")
        
        try:
            with transaction.atomic():
                # Créer les StockMovement pour chaque ligne
                for line in transfer.lines.all():
                    if not line.quantity_sent or line.quantity_sent <= 0:
                        # Si quantity_sent est vide, utiliser quantity_requested
                        quantity = line.quantity_requested or 0
                        if quantity <= 0:
                            print(f"     ⚠ Ligne ignorée: produit {line.product.name}, quantité nulle")
                            continue
                    else:
                        quantity = line.quantity_sent
                    
                    print(f"     + Produit: {line.product.name}, Quantité: {quantity}")
                    
                    # Créer le mouvement de transfert
                    movement = StockMovement.objects.create(
                        product=line.product,
                        store=transfer.source_store,
                        destination_store=transfer.destination_store,
                        movement_type='transfer',
                        quantity=quantity,
                        reference=transfer.transfer_number,
                        notes=f'Transfert vers {transfer.destination_store.name} (migration automatique)',
                        date=transfer.transfer_date,
                        created_by=transfer.validated_by or transfer.created_by
                    )
                    
                    print(f"       ✓ StockMovement créé (ID: {movement.id})")
                    
                    # Vérifier et ajuster le stock si nécessaire
                    # (normalement déjà fait lors de la validation, mais on vérifie)
                    try:
                        stock = Stock.objects.get(
                            product=line.product,
                            store=transfer.source_store
                        )
                        # Le stock devrait déjà être diminué, on vérifie juste
                        print(f"       -> Stock actuel magasin source: {stock.quantity}")
                    except Stock.DoesNotExist:
                        print(f"       ⚠ Stock non trouvé pour {line.product.name} dans {transfer.source_store.name}")
                
                fixed_count += 1
                print(f"     ✓ Transfert {transfer.transfer_number} corrigé avec succès!")
                
        except Exception as e:
            error_count += 1
            print(f"     ✗ ERREUR pour le transfert {transfer.transfer_number}: {str(e)}")
            continue
    
    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ")
    print("=" * 80)
    print(f"✓ Transferts corrigés: {fixed_count}")
    print(f"⊘ Transferts déjà OK (ignorés): {skipped_count}")
    print(f"✗ Erreurs: {error_count}")
    print(f"Total traité: {transfers.count()}")
    print("=" * 80)
    
    if fixed_count > 0:
        print("\n✓ Les anciens transferts apparaissent maintenant dans /mouvements/sortie et /mouvements")
    
    return fixed_count, skipped_count, error_count

# Auto-exécution
print("\nCe script va créer les StockMovement manquants pour les anciens transferts.")
print("Les transferts apparaîtront ensuite dans les listes de mouvements.\n")
print("Exécution automatique...\n")
fix_transfers()
