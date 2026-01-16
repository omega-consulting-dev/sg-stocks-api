#!/usr/bin/env python
"""
Script pour peupler le tenant de démo avec des données réalistes.
"""
import os
import sys
import django
from datetime import date, datetime, timedelta
from decimal import Decimal
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Company

def populate_demo_data():
    """Peupler le tenant démo avec des données"""
    print("="*80)
    print("PEUPLEMENT DES DONNÉES DE DÉMO")
    print("="*80)
    print()
    
    # Vérifier que le tenant démo existe
    demo = Company.objects.filter(schema_name='demo').first()
    if not demo:
        print("[ERREUR] Le tenant 'demo' n'existe pas!")
        print("   Exécutez d'abord: python create_demo_tenant.py")
        return False
    
    with schema_context('demo'):
        from apps.inventory.models import Store
        from apps.products.models import Product, ProductCategory
        from apps.customers.models import Customer
        from apps.suppliers.models import Supplier
        from apps.accounts.models import User
        
        print("🏪 Création des magasins...")
        stores_data = [
            {'name': 'Magasin Principal', 'code': 'MAG001', 'address': 'Douala, Akwa'},
            {'name': 'Succursale Bonamoussadi', 'code': 'MAG002', 'address': 'Douala, Bonamoussadi'},
        ]
        
        stores = []
        for store_data in stores_data:
            store, created = Store.objects.get_or_create(
                code=store_data['code'],
                defaults=store_data
            )
            stores.append(store)
            status = "[OK] Créé" if created else "♻️  Existe déjà"
            print(f"   {status}: {store.name}")
        
        print()
        print("📁 Création de la catégorie par défaut...")
        default_category, created = ProductCategory.objects.get_or_create(
            name='Produits Divers',
            defaults={'description': 'Catégorie par défaut pour les produits de démo'}
        )
        status = "[OK] Créée" if created else "♻️  Existe déjà"
        print(f"   {status}: {default_category.name}")
        
        print()
        print("[PACKAGE] Création des produits...")
        products_data = [
            {'name': 'iPhone 15 Pro', 'cost': 450000, 'price': 550000, 'ref': 'PROD-001'},
            {'name': 'Samsung Galaxy S24', 'cost': 380000, 'price': 480000, 'ref': 'PROD-002'},
            {'name': 'Chemise Homme', 'cost': 8000, 'price': 15000, 'ref': 'PROD-003'},
            {'name': 'Pantalon Jean', 'cost': 12000, 'price': 20000, 'ref': 'PROD-004'},
            {'name': 'Riz 50kg', 'cost': 18000, 'price': 25000, 'ref': 'PROD-005'},
            {'name': 'Huile végétale 5L', 'cost': 4500, 'price': 6000, 'ref': 'PROD-006'},
            {'name': 'Coca-Cola 1.5L', 'cost': 800, 'price': 1200, 'ref': 'PROD-007'},
            {'name': 'Eau minérale 1.5L', 'cost': 300, 'price': 500, 'ref': 'PROD-008'},
            {'name': 'Savon de Marseille', 'cost': 1000, 'price': 1500, 'ref': 'PROD-009'},
            {'name': 'Shampoing 500ml', 'cost': 2500, 'price': 3500, 'ref': 'PROD-010'},
        ]
        
        products = []
        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                reference=prod_data['ref'],
                defaults={
                    'name': prod_data['name'],
                    'category': default_category,
                    'barcode': f'978{random.randint(1000000000, 9999999999)}',
                    'cost_price': Decimal(str(prod_data['cost'])),
                    'selling_price': Decimal(str(prod_data['price'])),
                    'tax_rate': Decimal('19.25'),
                    'minimum_stock': 5,
                    'optimal_stock': 20,
                    'product_type': 'storable',
                    'is_for_sale': True,
                    'is_active': True
                }
            )
            products.append(product)
            status = "[OK] Créé" if created else "♻️  Existe déjà"
            print(f"   {status}: {product.name} ({product.reference})")
        
        print()
        print("👥 Création des clients...")
        customers_data = [
            {'name': 'Jean Dupont', 'customer_code': 'CLI-001', 'email': 'jean.dupont@email.cm', 'phone': '237690000001', 'payment_term': 'immediate'},
            {'name': 'Marie Kamga', 'customer_code': 'CLI-002', 'email': 'marie.kamga@email.cm', 'phone': '237690000002', 'payment_term': '15_days'},
            {'name': 'Paul Ngono', 'customer_code': 'CLI-003', 'email': 'paul.ngono@email.cm', 'phone': '237690000003', 'payment_term': '30_days'},
        ]
        
        for cust_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                customer_code=cust_data['customer_code'],
                defaults=cust_data
            )
            status = "[OK] Créé" if created else "♻️  Existe déjà"
            print(f"   {status}: {customer.name}")
        
        print()
        print("🏭 Création des fournisseurs...")
        suppliers_data = [
            {'name': 'TechPlus Sarl', 'supplier_code': 'FOUR-001', 'email': 'contact@techplus.cm', 'phone': '237690000010', 'payment_term': 'immediate'},
            {'name': 'Mode & Style', 'supplier_code': 'FOUR-002', 'email': 'info@modestyle.cm', 'phone': '237690000011', 'payment_term': '15_days'},
            {'name': 'Agro Distribution', 'supplier_code': 'FOUR-003', 'email': 'ventes@agrodist.cm', 'phone': '237690000012', 'payment_term': '30_days'},
        ]
        
        for supp_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                supplier_code=supp_data['supplier_code'],
                defaults=supp_data
            )
            status = "[OK] Créé" if created else "♻️  Existe déjà"
            print(f"   {status}: {supplier.name}")
        
        print()
        print("="*80)
        print("[OK] DONNÉES DE DÉMO CRÉÉES AVEC SUCCÈS!")
        print("="*80)
        print()
        print(f"   [STATS] Magasins    : {Store.objects.count()}")
        print(f"   [PACKAGE] Produits    : {Product.objects.count()}")
        print(f"   👥 Clients     : {Customer.objects.count()}")
        print(f"   🏭 Fournisseurs: {Supplier.objects.count()}")
        print()
        
    return True

if __name__ == '__main__':
    try:
        populate_demo_data()
    except Exception as e:
        print(f"[ERREUR] ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
