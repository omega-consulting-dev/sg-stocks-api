"""
Script pour supprimer les mouvements de stock en double avec référence VENTE-xxx
et remettre le stock à son état correct.

USAGE: python manage.py tenant_command cleanup_duplicate_movements --schema=<tenant_name>
"""

def cleanup_vente_movements():
    """Supprimer tous les mouvements avec référence VENTE-xxx et remettre le stock."""
    from apps.inventory.models import StockMovement, Stock
    
    # Trouver tous les mouvements avec référence commençant par "VENTE-"
    vente_movements = StockMovement.objects.filter(reference__startswith='VENTE-')
    
    total_movements = vente_movements.count()
    print(f"\n{'='*60}")
    print(f"Trouvé {total_movements} mouvements avec référence VENTE-xxx")
    print(f"{'='*60}\n")
    
    if total_movements == 0:
        print("✅ Aucun mouvement à supprimer.")
        return
    
    # Grouper par produit pour afficher le résumé
    movements_by_product = {}
    for movement in vente_movements:
        if movement.product:
            product_name = movement.product.name
            if product_name not in movements_by_product:
                movements_by_product[product_name] = []
            movements_by_product[product_name].append(movement)
    
    print("📋 Résumé des mouvements à supprimer :\n")
    for product_name, movements in movements_by_product.items():
        total_qty = sum(m.quantity for m in movements)
        print(f"  • {product_name}: {len(movements)} mouvement(s), total: {total_qty} unités")
    
    # Demander confirmation
    print(f"\n{'='*60}")
    response = input("⚠️  Voulez-vous vraiment supprimer ces mouvements ? (oui/non): ")
    print(f"{'='*60}\n")
    
    if response.lower() not in ['oui', 'o', 'yes', 'y']:
        print("❌ Opération annulée.")
        return
    
    # Remettre le stock et supprimer les mouvements
    corrected_stocks = {}
    deleted_count = 0
    
    for movement in vente_movements:
        if movement.product:
            try:
                stock = Stock.objects.get(
                    product=movement.product,
                    store=movement.store
                )
                
                # Annuler le mouvement (remettre le stock)
                if movement.movement_type == 'out':
                    stock.quantity += movement.quantity
                    stock.save()
                    
                    # Tracker les corrections
                    key = f"{movement.product.name} ({movement.store.name})"
                    if key not in corrected_stocks:
                        corrected_stocks[key] = 0
                    corrected_stocks[key] += movement.quantity
                
            except Stock.DoesNotExist:
                print(f"⚠️  Stock non trouvé pour {movement.product.name}")
        
        # Supprimer le mouvement
        movement.delete()
        deleted_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ {deleted_count} mouvements supprimés avec succès !")
    print(f"{'='*60}\n")
    
    if corrected_stocks:
        print("📊 Stocks corrigés (quantités remises) :\n")
        for product_store, qty in corrected_stocks.items():
            print(f"  • {product_store}: +{qty} unités")
    
    print(f"\n{'='*60}")
    print("✅ Nettoyage terminé !")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    cleanup_vente_movements()
