"""
Commande Django pour supprimer les factures et leurs mouvements de stock
Usage: python manage.py tenant_command delete_all_invoices --schema=<tenant_name>
"""
from django.core.management.base import BaseCommand
from apps.invoicing.models import Invoice
from apps.sales.models import Sale
from apps.inventory.models import StockMovement, Stock


class Command(BaseCommand):
    help = 'Supprimer toutes les factures et remettre les stocks'

    def handle(self, *args, **options):
        # Compter les factures et mouvements
        invoices = Invoice.objects.all()
        invoice_count = invoices.count()
        
        fact_movements = StockMovement.objects.filter(reference__startswith='FACT-')
        movement_count = fact_movements.count()
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING(f"Trouvé {invoice_count} factures"))
        self.stdout.write(self.style.WARNING(f"Trouvé {movement_count} mouvements FACT-xxx"))
        self.stdout.write("="*60 + "\n")
        
        if invoice_count == 0 and movement_count == 0:
            self.stdout.write(self.style.SUCCESS("✅ Aucune facture ou mouvement à supprimer."))
            return
        
        # Afficher le détail des mouvements
        if movement_count > 0:
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
        response = input("⚠️  Voulez-vous VRAIMENT supprimer TOUTES les factures ? (oui/non): ")
        self.stdout.write("="*60 + "\n")
        
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            self.stdout.write(self.style.ERROR("❌ Opération annulée."))
            return
        
        # Remettre le stock pour les mouvements FACT-xxx
        corrected_stocks = {}
        
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
        
        # Supprimer les mouvements FACT-xxx
        deleted_movements = fact_movements.count()
        fact_movements.delete()
        
        # Remettre les ventes en statut draft
        Sale.objects.all().update(status='draft')
        
        # Supprimer toutes les factures
        deleted_invoices = invoices.count()
        invoices.delete()
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"✅ {deleted_invoices} factures supprimées"))
        self.stdout.write(self.style.SUCCESS(f"✅ {deleted_movements} mouvements supprimés"))
        self.stdout.write(self.style.SUCCESS(f"✅ Toutes les ventes remises en statut 'draft'"))
        self.stdout.write("="*60 + "\n")
        
        if corrected_stocks:
            self.stdout.write(self.style.SUCCESS("📊 Stocks remis à leur état d'origine :\n"))
            for product_store, qty in corrected_stocks.items():
                self.stdout.write(f"  • {product_store}: +{qty} unités")
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("✅ Nettoyage complet terminé !"))
        self.stdout.write("="*60 + "\n")
