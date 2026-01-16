"""
Commandes pour corriger manuellement le stock dans le shell Django.
Exécutez: python manage.py tenant_command shell --schema=agribio
Puis copiez-collez ces commandes :
"""

# 1. Importer les modèles nécessaires
from apps.inventory.models import Stock, Store
from apps.products.models import Product
from django.db import transaction

# 2. Trouver le produit
product = Product.objects.filter(reference='PROD001').first()
print(f"Produit: {product.name if product else 'NON TROUVÉ'}")

# 3. Trouver le magasin
store = Store.objects.filter(name__icontains='Douala').first()
print(f"Magasin: {store.name if store else 'NON TROUVÉ'}")

# 4. Trouver le stock
stock = Stock.objects.filter(product=product, store=store).first()
print(f"Stock actuel: {stock.quantity if stock else 'NON TROUVÉ'}")

# 5. Calculer la correction
expected = 249
if stock:
    difference = expected - stock.quantity
    print(f"Stock attendu: {expected}")
    print(f"Différence: {difference}")
    
    # 6. Appliquer la correction
    if difference != 0:
        confirm = input(f"Ajouter {difference} unités ? (oui/non): ")
        if confirm.lower() in ['oui', 'o', 'yes', 'y']:
            with transaction.atomic():
                stock.quantity += difference
                stock.save()
                print(f"✅ Stock corrigé: {stock.quantity}")
        else:
            print("❌ Annulé")
    else:
        print("✅ Stock déjà correct")
