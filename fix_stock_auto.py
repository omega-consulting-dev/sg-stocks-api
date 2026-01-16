"""
Script automatique pour corriger le stock après le bug d'annulation.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import transaction
from apps.inventory.models import Stock, Store
from apps.products.models import Product

def fix_stock_auto():
    """Corriger automatiquement le stock."""
    
    try:
        # Chercher le produit "Agri bio fongicide 1L"
        product = Product.objects.filter(reference='PROD001').first()
        if not product:
            print("❌ Produit PROD001 non trouvé.")
            return
        
        print(f"✅ Produit trouvé: {product.name}")
        
        # Chercher le magasin PV Douala
        store = Store.objects.filter(name__icontains='PV Douala').first()
        if not store:
            print("❌ Magasin 'PV Douala' non trouvé.")
            # Essayer avec "Douala"
            store = Store.objects.filter(name__icontains='Douala').first()
            if not store:
                print("❌ Aucun magasin contenant 'Douala' trouvé.")
                return
        
        print(f"✅ Magasin trouvé: {store.name}")
        
        # Chercher le stock
        stock = Stock.objects.filter(product=product, store=store).first()
        if not stock:
            print(f"❌ Stock non trouvé.")
            return
        
        print(f"\n📊 Stock actuel: {stock.quantity}")
        
        # Le stock devrait être 249 (250 - 1 vente)
        # Mais il est à 198
        # Différence: 249 - 198 = 51
        
        expected_stock = 249
        difference = expected_stock - stock.quantity
        
        print(f"📈 Stock attendu: {expected_stock}")
        print(f"➕ Différence à corriger: {difference}")
        
        if difference > 0:
            with transaction.atomic():
                stock.quantity += difference
                stock.save()
                print(f"\n✅ Stock corrigé !")
                print(f"📦 Nouveau stock: {stock.quantity}")
        elif difference < 0:
            print(f"\n⚠️  Le stock actuel est SUPÉRIEUR à l'attendu de {abs(difference)} unités.")
        else:
            print(f"\n✅ Le stock est déjà correct.")
    
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 CORRECTION AUTOMATIQUE DU STOCK")
    print("=" * 60)
    fix_stock_auto()
