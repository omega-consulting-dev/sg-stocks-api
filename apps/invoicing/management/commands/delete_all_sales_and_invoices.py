"""
Commande Django pour supprimer toutes les factures, ventes et remettre les stocks d'origine
Usage: python manage.py tenant_command delete_all_sales_and_invoices --schema=<tenant_name>
"""
from django.core.management.base import BaseCommand
from apps.sales.models import Sale
from apps.invoicing.models import Invoice
from apps.inventory.models import StockMovement, Stock


class Command(BaseCommand):
    help = 'Supprimer toutes les ventes, factures et remettre les stocks d\'origine'

    def handle(self, *args, **options):
        # Récupérer toutes les ventes et factures
        sales = Sale.objects.all()
        invoices = Invoice.objects.all()
        fact_movements = StockMovement.objects.filter(reference__startswith='FACT-')
        
        total_sales = sales.count()
        total_invoices = invoices.count()
        total_movements = fact_movements.count()
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING(f"Éléments à supprimer :"))
        self.stdout.write(f"  • {total_sales} vente(s)")
        self.stdout.write(f"  • {total_invoices} facture(s)")
        self.stdout.write(f"  • {total_movements} mouvement(s) FACT-xxx")
        self.stdout.write("="*60 + "\n")
        
        if total_movements == 0 and total_invoices == 0 and total_sales == 0:
            self.stdout.write(self.style.SUCCESS("✅ Aucune donnée à supprimer."))
            return
        
        # Afficher les mouvements de stock par produit
        if total_movements > 0:
            movements_by_product = {}
            for movement in fact_movements:
                if movement.product:
                    product_name = movement.product.name
                    if product_name not in movements_by_product:
                        movements_by_product[product_name] = []
                    movements_by_product[product_name].append(movement)
            
            self.stdout.write(self.style.WARNING("📋 Mouvements de stock à annuler :\n"))
            for product_name, movements in movements_by_product.items():
                total_qty = sum(m.quantity for m in movements)
                self.stdout.write(f"  • {product_name}: {len(movements)} mouvement(s), total: {total_qty} unités")
        
        # Demander confirmation
        self.stdout.write("\n" + "="*60)
        response = input("⚠️  ATTENTION : Cela va supprimer TOUTES les ventes et factures et remettre les stocks d'origine.\nVoulez-vous continuer ? (oui/non): ")
        self.stdout.write("="*60 + "\n")
        
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            self.stdout.write(self.style.ERROR("❌ Opération annulée."))
            return
        
        # 1. Remettre les stocks en annulant les mouvements FACT-xxx
        corrected_stocks = {}
        movements_deleted = 0
        
        for movement in fact_movements:
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
            movements_deleted += 1
        
        # 2. Supprimer les factures
        invoices_deleted = invoices.count()
        invoices.delete()
        
        # 3. Supprimer les ventes
        sales_deleted = sales.count()
        sales.delete()
        
        # Afficher le résumé
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"✅ Suppression terminée :"))
        self.stdout.write(f"  • {movements_deleted} mouvement(s) supprimé(s)")
        self.stdout.write(f"  • {invoices_deleted} facture(s) supprimée(s)")
        self.stdout.write(f"  • {sales_deleted} vente(s) supprimée(s)")
        self.stdout.write("="*60 + "\n")
        
        if corrected_stocks:
            self.stdout.write(self.style.SUCCESS("📊 Stocks remis à l'état d'origine :\n"))
            for product_store, qty in corrected_stocks.items():
                self.stdout.write(f"  • {product_store}: +{qty} unités")
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("✅ Les stocks sont maintenant à leur état d'origine !"))
        self.stdout.write("="*60 + "\n")
