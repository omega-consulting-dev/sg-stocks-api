#!/usr/bin/env python
"""
Script pour créer les mouvements de stock manquants pour les factures existantes
et tester la nouvelle fonctionnalité
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from apps.invoicing.models import Invoice, create_stock_movements_from_invoice
from apps.inventory.models import StockMovement, Stock
from decimal import Decimal

def fix_missing_stock_movements():
    """Crée les mouvements de stock manquants pour les factures existantes."""
    
    tenants = ['agribio', 'saker', 'demo']
    
    for tenant_name in tenants:
        print(f"\n{'='*60}")
        print(f"🔍 Analyse du tenant: {tenant_name.upper()}")
        print('='*60)
        
        with schema_context(tenant_name):
            # Récupérer toutes les factures
            invoices = Invoice.objects.all()
            
            if invoices.count() == 0:
                print("ℹ️  Aucune facture trouvée.")
                continue
            
            print(f"\n📊 Nombre total de factures: {invoices.count()}")
            
            # Vérifier chaque facture
            factures_sans_mouvement = []
            
            for invoice in invoices:
                # Vérifier si la facture a des lignes avec des produits
                product_lines = invoice.lines.filter(product__isnull=False)
                
                if product_lines.count() == 0:
                    continue  # Facture de services uniquement
                
                # Vérifier si des mouvements existent pour cette facture
                movements = StockMovement.objects.filter(
                    reference=f"FACT-{invoice.invoice_number}"
                )
                
                if movements.count() == 0:
                    factures_sans_mouvement.append(invoice)
                    print(f"\n⚠️  Facture {invoice.invoice_number} sans mouvements de stock!")
                    print(f"   - Client: {invoice.customer.name if invoice.customer else 'N/A'}")
                    print(f"   - Date: {invoice.invoice_date}")
                    print(f"   - Montant: {invoice.total_amount} FCFA")
                    print(f"   - Lignes produits: {product_lines.count()}")
            
            if len(factures_sans_mouvement) == 0:
                print("\n✅ Toutes les factures ont leurs mouvements de stock!")
                continue
            
            print(f"\n{'='*60}")
            print(f"📋 Résumé: {len(factures_sans_mouvement)} facture(s) sans mouvements")
            print('='*60)
            
            # Demander confirmation avant de créer les mouvements
            if len(factures_sans_mouvement) > 0:
                reponse = input(f"\n⚠️  Voulez-vous créer les mouvements manquants pour ces {len(factures_sans_mouvement)} facture(s)? (oui/non): ")
                
                if reponse.lower() != 'oui':
                    print("❌ Opération annulée.")
                    continue
                
                # Créer les mouvements manquants
                mouvements_crees = 0
                erreurs = 0
                
                for invoice in factures_sans_mouvement:
                    try:
                        print(f"\n🔄 Traitement de la facture {invoice.invoice_number}...")
                        
                        # Vérifier le stock disponible pour chaque produit
                        stock_ok = True
                        for line in invoice.lines.filter(product__isnull=False):
                            stock = Stock.objects.filter(
                                product=line.product,
                                store=invoice.store
                            ).first()
                            
                            if not stock or stock.quantity < line.quantity:
                                available = stock.quantity if stock else 0
                                print(f"   ❌ Stock insuffisant pour {line.product.name}")
                                print(f"      Disponible: {available}, Demandé: {line.quantity}")
                                stock_ok = False
                                break
                        
                        if not stock_ok:
                            print(f"   ⚠️  Impossible de créer les mouvements (stock insuffisant)")
                            erreurs += 1
                            continue
                        
                        # Créer les mouvements
                        create_stock_movements_from_invoice(
                            sender=Invoice,
                            instance=invoice,
                            created=True
                        )
                        
                        # Vérifier que les mouvements ont été créés
                        movements = StockMovement.objects.filter(
                            reference=f"FACT-{invoice.invoice_number}"
                        )
                        
                        print(f"   ✅ {movements.count()} mouvement(s) créé(s)")
                        mouvements_crees += movements.count()
                        
                    except Exception as e:
                        print(f"   ❌ Erreur: {str(e)}")
                        erreurs += 1
                        import traceback
                        traceback.print_exc()
                
                print(f"\n{'='*60}")
                print(f"✅ Terminé!")
                print(f"   - Mouvements créés: {mouvements_crees}")
                print(f"   - Erreurs: {erreurs}")
                print('='*60)

def test_nouvelle_vente():
    """Teste la création d'une nouvelle vente pour vérifier que le stock diminue."""
    print(f"\n{'='*60}")
    print("🧪 TEST: Création d'une vente et vérification du stock")
    print('='*60)
    
    tenant_name = input("\nEntrez le nom du tenant pour le test (agribio/saker/demo): ")
    
    with schema_context(tenant_name):
        # Lister les produits disponibles
        stocks = Stock.objects.filter(quantity__gt=0)[:5]
        
        if stocks.count() == 0:
            print("❌ Aucun produit en stock pour le test.")
            return
        
        print("\n📦 Produits disponibles:")
        for i, stock in enumerate(stocks, 1):
            print(f"   {i}. {stock.product.name} - Stock: {stock.quantity}")
        
        print("\nℹ️  Pour créer une vente de test:")
        print("   1. Allez sur l'interface web")
        print("   2. Créez une nouvelle vente avec un des produits ci-dessus")
        print("   3. Confirmez la vente")
        print("   4. Vérifiez que le stock a diminué")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔧 CORRECTION DES MOUVEMENTS DE STOCK MANQUANTS")
    print("="*60)
    
    print("\nCe script va:")
    print("  1. Analyser toutes les factures existantes")
    print("  2. Identifier celles sans mouvements de stock")
    print("  3. Créer les mouvements manquants (avec votre confirmation)")
    
    fix_missing_stock_movements()
    
    print("\n" + "="*60)
    test_nouvelle_vente()
