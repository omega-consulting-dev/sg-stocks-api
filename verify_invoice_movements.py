#!/usr/bin/env python
"""
Script pour vérifier les mouvements de stock d'une facture spécifique
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from apps.invoicing.models import Invoice
from apps.inventory.models import StockMovement, Stock

def verify_invoice_movements():
    """Vérifie les mouvements de stock pour une facture."""
    
    with schema_context('saker'):
        # Récupérer la facture FAC2026000001
        invoice = Invoice.objects.filter(invoice_number='FAC2026000001').first()
        
        if not invoice:
            print("❌ Facture non trouvée")
            return
        
        print("="*60)
        print(f"📋 FACTURE: {invoice.invoice_number}")
        print("="*60)
        print(f"Client: {invoice.customer.name if invoice.customer else 'N/A'}")
        print(f"Date: {invoice.invoice_date}")
        print(f"Montant total: {invoice.total_amount} FCFA")
        print(f"Statut: {invoice.status}")
        
        print(f"\n{'='*60}")
        print("📦 LIGNES DE LA FACTURE:")
        print('='*60)
        
        for line in invoice.lines.all():
            if line.product:
                print(f"\nProduit: {line.product.name}")
                print(f"  - Référence: {line.product.reference}")
                print(f"  - Quantité: {line.quantity}")
                print(f"  - Prix unitaire: {line.unit_price} FCFA")
                print(f"  - Total ligne: {line.total} FCFA")
                
                # Récupérer le stock actuel
                stock = Stock.objects.filter(
                    product=line.product,
                    store=invoice.store
                ).first()
                
                if stock:
                    print(f"  - Stock actuel: {stock.quantity}")
        
        print(f"\n{'='*60}")
        print("📊 MOUVEMENTS DE STOCK ASSOCIÉS:")
        print('='*60)
        
        movements = StockMovement.objects.filter(
            reference=f"FACT-{invoice.invoice_number}"
        )
        
        if movements.count() == 0:
            print("\n❌ Aucun mouvement de stock trouvé!")
        else:
            print(f"\n✅ {movements.count()} mouvement(s) trouvé(s):")
            
            for movement in movements:
                print(f"\n  Mouvement #{movement.id}:")
                print(f"    - Type: {movement.get_movement_type_display()}")
                print(f"    - Produit: {movement.product.name}")
                print(f"    - Magasin: {movement.store.name}")
                print(f"    - Quantité: {movement.quantity}")
                print(f"    - Valeur: {movement.total_value} FCFA")
                print(f"    - Référence: {movement.reference}")
                print(f"    - Date: {movement.date}")
                print(f"    - Notes: {movement.notes}")
        
        print("\n" + "="*60)

if __name__ == '__main__':
    verify_invoice_movements()
