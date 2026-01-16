from apps.inventory.models import StockMovement
from django.db.models import Count

print("=== VÉRIFICATION DES TRANSFERTS ===\n")

# Compter les transferts
total_transfers = StockMovement.objects.filter(movement_type='transfer').count()
print(f"Total de mouvements de type 'transfer': {total_transfers}\n")

# Afficher les 5 derniers transferts
print("Les 5 derniers transferts:")
transfers = StockMovement.objects.filter(movement_type='transfer').order_by('-created_at')[:5]

if transfers:
    for t in transfers:
        dest = t.destination_store.name if t.destination_store else 'N/A'
        print(f"ID: {t.id}, Produit: {t.product.name}, Qté: {t.quantity}, Source: {t.store.name}, Dest: {dest}, Date: {t.date}")
else:
    print("Aucun transfert trouvé")

# Vérifier tous les types
print("\n=== TYPES DE MOUVEMENTS ===")
movement_types = StockMovement.objects.values('movement_type').annotate(count=Count('id'))
for mt in movement_types:
    print(f"{mt['movement_type']}: {mt['count']}")
