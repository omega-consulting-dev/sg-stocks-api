"""
Script pour créer rétroactivement les mouvements de stock
pour les ventes existantes qui n'en ont pas.
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from apps.sales.models import Sale
from apps.inventory.models import StockMovement, Stock
from django.db import transaction


def create_missing_movements():
    """Créer les mouvements manquants pour les ventes confirmées."""
    
    # Récupérer toutes les ventes confirmées ou complétées
    confirmed_sales = Sale.objects.filter(
        status__in=['confirmed', 'completed']
    ).prefetch_related('lines', 'lines__product')
    
    print(f"Trouvé {confirmed_sales.count()} vente(s) confirmée(s)")
    
    created_count = 0
    skipped_count = 0
    
    for sale in confirmed_sales:
        # Vérifier si des mouvements existent déjà pour cette vente
        existing_movements = StockMovement.objects.filter(
            reference=f"VENTE-{sale.sale_number}"
        ).exists()
        
        if existing_movements:
            print(f"  ✓ Vente {sale.sale_number} a déjà des mouvements - ignoré")
            skipped_count += 1
            continue
        
        print(f"\n  → Vente {sale.sale_number} - Création des mouvements...")
        
        # Créer les mouvements pour chaque ligne de produit
        with transaction.atomic():
            for line in sale.lines.filter(line_type='product', product__isnull=False):
                try:
                    # Créer le mouvement de sortie
                    movement = StockMovement.objects.create(
                        product=line.product,
                        store=sale.store,
                        movement_type='out',
                        quantity=line.quantity,
                        total_value=line.total,
                        reference=f"VENTE-{sale.sale_number}",
                        notes=f"Sortie automatique - Vente {sale.sale_number}" + (
                            f" - Client: {sale.customer.name}" if sale.customer else ""
                        ),
                        created_by=sale.created_by,
                        is_active=True
                    )
                    
                    print(f"    ✓ Mouvement créé pour {line.product.name} (qty: {line.quantity})")
                    created_count += 1
                    
                except Exception as e:
                    print(f"    ✗ Erreur pour {line.product.name}: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"Résumé:")
    print(f"  - Mouvements créés: {created_count}")
    print(f"  - Ventes ignorées (déjà OK): {skipped_count}")
    print(f"{'='*60}")


if __name__ == '__main__':
    print("="*60)
    print("Création des mouvements de stock manquants")
    print("="*60)
    
    confirmation = input("\nContinuer? (oui/non): ")
    if confirmation.lower() in ['oui', 'o', 'yes', 'y']:
        create_missing_movements()
        print("\n✓ Terminé!")
    else:
        print("\nAnnulé.")
