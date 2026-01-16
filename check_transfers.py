#!/usr/bin/env python
"""Script pour vérifier les mouvements de type transfer"""
import os
import sys
import django

# Ajouter le répertoire du projet au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.urls')
os.environ['DJANGO_SETTINGS_MODULE'] = 'myproject.settings'
django.setup()

from apps.inventory.models import StockMovement

print("=== VÉRIFICATION DES TRANSFERTS ===\n")

# Compter les transferts
total_transfers = StockMovement.objects.filter(movement_type='transfer').count()
print(f"Total de mouvements de type 'transfer': {total_transfers}\n")

# Afficher les 10 derniers transferts
print("Les 10 derniers transferts:")
transfers = StockMovement.objects.filter(movement_type='transfer').order_by('-created_at')[:10]

if transfers:
    for t in transfers:
        print(f"  ID: {t.id}")
        print(f"  Produit: {t.product.name}")
        print(f"  Quantité: {t.quantity}")
        print(f"  Magasin source: {t.store.name}")
        print(f"  Magasin destination: {t.destination_store.name if t.destination_store else 'N/A'}")
        print(f"  Date: {t.date}")
        print(f"  Référence: {t.reference}")
        print(f"  Créé le: {t.created_at}")
        print("-" * 50)
else:
    print("  Aucun transfert trouvé")

# Vérifier tous les types de mouvements
print("\n=== TOUS LES TYPES DE MOUVEMENTS ===")
from django.db.models import Count
movement_types = StockMovement.objects.values('movement_type').annotate(count=Count('id'))
for mt in movement_types:
    print(f"  {mt['movement_type']}: {mt['count']}")
