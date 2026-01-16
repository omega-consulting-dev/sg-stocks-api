"""
Script pour corriger les stocks après le bug d'annulation de transfert.
Le bug: lors de l'annulation d'un transfert reçu, on utilisait quantity_sent au lieu de quantity_received
pour remettre le stock à la source.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.db import transaction
from apps.inventory.models import Stock, StockTransfer
from apps.products.models import Product
from apps.tenants.models import Store

def fix_stock_after_cancel():
    """
    Corriger le stock du produit après l'annulation incorrecte du transfert.
    """
    
    # Nom du tenant
    tenant_name = input("Entrez le nom du tenant (par défaut: agribio): ").strip() or "agribio"
    
    # Nom du produit
    product_name = input("Entrez le nom du produit (par défaut: Agri bio fongicide 1L): ").strip() or "Agri bio fongicide 1L"
    
    # Nom du magasin à corriger
    store_name = input("Entrez le nom du magasin à corriger (par défaut: PV Douala): ").strip() or "PV Douala"
    
    # Quantité à ajouter
    quantity_str = input("Entrez la quantité à ajouter (par défaut: 51): ").strip() or "51"
    quantity_to_add = int(quantity_str)
    
    print(f"\n🔍 Recherche du produit '{product_name}' dans le tenant '{tenant_name}'...")
    
    try:
        # Chercher le produit
        product = Product.objects.filter(name__icontains=product_name).first()
        if not product:
            print(f"❌ Produit '{product_name}' non trouvé.")
            return
        
        print(f"✅ Produit trouvé: {product.name} (Ref: {product.reference})")
        
        # Chercher le magasin
        store = Store.objects.filter(name__icontains=store_name).first()
        if not store:
            print(f"❌ Magasin '{store_name}' non trouvé.")
            return
        
        print(f"✅ Magasin trouvé: {store.name}")
        
        # Chercher le stock
        stock = Stock.objects.filter(product=product, store=store).first()
        if not stock:
            print(f"❌ Stock non trouvé pour ce produit dans ce magasin.")
            return
        
        print(f"\n📊 Stock actuel: {stock.quantity}")
        print(f"➕ Quantité à ajouter: {quantity_to_add}")
        print(f"📈 Nouveau stock: {stock.quantity + quantity_to_add}")
        
        confirm = input("\n⚠️  Voulez-vous appliquer cette correction ? (oui/non): ").strip().lower()
        
        if confirm in ['oui', 'o', 'yes', 'y']:
            with transaction.atomic():
                stock.quantity += quantity_to_add
                stock.save()
                print(f"\n✅ Stock corrigé avec succès !")
                print(f"📦 Nouveau stock: {stock.quantity}")
        else:
            print("\n❌ Correction annulée.")
    
    except Exception as e:
        print(f"\n❌ Erreur: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 CORRECTION DU STOCK APRÈS ANNULATION DE TRANSFERT")
    print("=" * 60)
    fix_stock_after_cancel()
