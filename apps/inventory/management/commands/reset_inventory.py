"""
Commande Django pour supprimer toutes les données d'inventaire et paiements.
Usage: python manage.py reset_inventory --schema=<tenant_schema>
"""

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = 'Supprime toutes les données d\'inventaire, paiements et dettes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Schema du tenant (ex: tenant1, tenant2)',
            required=False
        )

    def handle(self, *args, **options):
        schema_name = options.get('schema')
        
        if not schema_name:
            self.stdout.write(self.style.ERROR(
                "❌ Erreur: Vous devez spécifier le schema du tenant avec --schema=<nom_schema>"
            ))
            self.stdout.write("\nExemple: python manage.py reset_inventory --schema=tenant1")
            return
        
        # Importer les modèles dans le contexte du schema
        with schema_context(schema_name):
            from apps.inventory.models import StockMovement, Stock, StockTransfer, StockTransferLine, Inventory, InventoryLine
            from apps.suppliers.models import SupplierPayment, PurchaseOrder, PurchaseOrderLine
            
            self._reset_data(StockMovement, Stock, StockTransfer, StockTransferLine, 
                           Inventory, InventoryLine, SupplierPayment, PurchaseOrder, PurchaseOrderLine)
    
    def _reset_data(self, StockMovement, Stock, StockTransfer, StockTransferLine, 
                    Inventory, InventoryLine, SupplierPayment, PurchaseOrder, PurchaseOrderLine):
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.WARNING("SUPPRESSION DE TOUTES LES DONNÉES D'INVENTAIRE"))
        self.stdout.write("=" * 70)
        
        # Compter les données
        self.stdout.write("\n📊 DONNÉES ACTUELLES:")
        self.stdout.write(f"   - Mouvements de stock: {StockMovement.objects.count()}")
        self.stdout.write(f"   - Stocks: {Stock.objects.count()}")
        self.stdout.write(f"   - Transferts: {StockTransfer.objects.count()}")
        self.stdout.write(f"   - Lignes de transfert: {StockTransferLine.objects.count()}")
        self.stdout.write(f"   - Inventaires: {Inventory.objects.count()}")
        self.stdout.write(f"   - Lignes d'inventaire: {InventoryLine.objects.count()}")
        self.stdout.write(f"   - Paiements fournisseurs: {SupplierPayment.objects.count()}")
        self.stdout.write(f"   - Lignes de commande: {PurchaseOrderLine.objects.count()}")
        self.stdout.write(f"   - Bons de commande: {PurchaseOrder.objects.count()}")
        
        # Confirmation
        confirmation = input("\n⚠️  VOULEZ-VOUS VRAIMENT SUPPRIMER CES DONNÉES? (tapez 'OUI' pour confirmer): ")
        
        if confirmation != 'OUI':
            self.stdout.write(self.style.ERROR("\n❌ Opération annulée."))
            return
        
        self.stdout.write("\n🔄 Suppression en cours...\n")
        
        # Supprimer dans l'ordre pour respecter les contraintes
        
        # 1. Inventaires
        count = InventoryLine.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} lignes d'inventaire supprimées"))
        
        count = Inventory.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} inventaires supprimés"))
        
        # 2. Transferts
        count = StockTransferLine.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} lignes de transfert supprimées"))
        
        count = StockTransfer.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} transferts supprimés"))
        
        # 3. Mouvements de stock
        count = StockMovement.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} mouvements de stock supprimés"))
        
        # 4. Stocks
        count = Stock.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} stocks supprimés"))
        
        # 5. Paiements fournisseurs
        count = SupplierPayment.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} paiements fournisseurs supprimés"))
        
        # 6. Lignes de commande
        count = PurchaseOrderLine.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} lignes de commande supprimées"))
        
        # 7. Bons de commande
        count = PurchaseOrder.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ {count} bons de commande supprimés"))
        
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("✅ TOUTES LES DONNÉES ONT ÉTÉ SUPPRIMÉES AVEC SUCCÈS!"))
        self.stdout.write("=" * 70)
        self.stdout.write("\n📋 Vous pouvez maintenant recommencer vos tests.")
        self.stdout.write("   Les produits, fournisseurs, clients et magasins sont conservés.\n")
