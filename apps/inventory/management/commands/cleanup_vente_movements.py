"""
Commande Django pour nettoyer les mouvements en double VENTE-xxx
Usage: python manage.py cleanup_vente_movements
"""
from django.core.management.base import BaseCommand
from apps.inventory.models import StockMovement, Stock


class Command(BaseCommand):
    help = 'Supprimer les mouvements avec référence VENTE-xxx et remettre le stock'

    def handle(self, *args, **options):
        # Trouver tous les mouvements avec référence commençant par "VENTE-"
        vente_movements = StockMovement.objects.filter(reference__startswith='VENTE-')
        
        total_movements = vente_movements.count()
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING(f"Trouvé {total_movements} mouvements avec référence VENTE-xxx"))
        self.stdout.write("="*60 + "\n")
        
        if total_movements == 0:
            self.stdout.write(self.style.SUCCESS("✅ Aucun mouvement à supprimer."))
            return
        
        # Grouper par produit pour afficher le résumé
        movements_by_product = {}
        for movement in vente_movements:
            if movement.product:
                product_name = movement.product.name
                if product_name not in movements_by_product:
                    movements_by_product[product_name] = []
                movements_by_product[product_name].append(movement)
        
        self.stdout.write(self.style.WARNING("📋 Résumé des mouvements à supprimer :\n"))
        for product_name, movements in movements_by_product.items():
            total_qty = sum(m.quantity for m in movements)
            self.stdout.write(f"  • {product_name}: {len(movements)} mouvement(s), total: {total_qty} unités")
        
        # Demander confirmation
        self.stdout.write("\n" + "="*60)
        response = input("⚠️  Voulez-vous vraiment supprimer ces mouvements ? (oui/non): ")
        self.stdout.write("="*60 + "\n")
        
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            self.stdout.write(self.style.ERROR("❌ Opération annulée."))
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
                    self.stdout.write(self.style.WARNING(f"⚠️  Stock non trouvé pour {movement.product.name}"))
            
            # Supprimer le mouvement
            movement.delete()
            deleted_count += 1
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"✅ {deleted_count} mouvements supprimés avec succès !"))
        self.stdout.write("="*60 + "\n")
        
        if corrected_stocks:
            self.stdout.write(self.style.SUCCESS("📊 Stocks corrigés (quantités remises) :\n"))
            for product_store, qty in corrected_stocks.items():
                self.stdout.write(f"  • {product_store}: +{qty} unités")
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("✅ Nettoyage terminé !"))
        self.stdout.write("="*60 + "\n")
