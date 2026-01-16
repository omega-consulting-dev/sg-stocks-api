"""
Commande Django pour vérifier et corriger la cohérence des stocks.
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum
from decimal import Decimal
from apps.inventory.models import Stock, StockMovement


class Command(BaseCommand):
    help = 'Vérifie et corrige la cohérence des stocks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Corriger les incohérences trouvées',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("VÉRIFICATION DE LA COHÉRENCE DES STOCKS"))
        self.stdout.write("=" * 80 + "\n")
        
        # 1. Afficher les statistiques des mouvements
        total_movements = StockMovement.objects.count()
        active_movements = StockMovement.objects.filter(is_active=True).count()
        inactive_movements = StockMovement.objects.filter(is_active=False).count()
        
        self.stdout.write("[STATS] STATISTIQUES DES MOUVEMENTS:")
        self.stdout.write(f"   - Total mouvements : {total_movements}")
        self.stdout.write(f"   - Mouvements actifs : {active_movements}")
        self.stdout.write(f"   - Mouvements inactifs (supprimés) : {inactive_movements}")
        
        if inactive_movements > 0:
            self.stdout.write(self.style.WARNING(
                f"\n[ATTENTION]  ATTENTION: {inactive_movements} mouvement(s) ont été supprimé(s)"
            ))
            self.stdout.write("   Ces mouvements ont été désactivés mais leur impact sur le stock")
            self.stdout.write("   a normalement été annulé lors de la suppression.\n")
        
        # 2. Vérifier chaque produit/magasin
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("VÉRIFICATION PRODUIT PAR PRODUIT")
        self.stdout.write("=" * 80 + "\n")
        
        stocks = Stock.objects.select_related('product', 'store').all()
        issues_found = []
        
        for stock in stocks:
            # Calculer le stock théorique basé sur les mouvements ACTIFS uniquement
            movements = StockMovement.objects.filter(
                product=stock.product,
                store=stock.store,
                is_active=True  # Seulement les mouvements actifs
            )
            
            entrees = movements.filter(movement_type='in').aggregate(
                total=Sum('quantity')
            )['total'] or Decimal('0')
            
            sorties = movements.filter(movement_type='out').aggregate(
                total=Sum('quantity')
            )['total'] or Decimal('0')
            
            # Transferts sortants
            transferts_out = movements.filter(movement_type='transfer').aggregate(
                total=Sum('quantity')
            )['total'] or Decimal('0')
            
            # Transferts entrants (mouvements vers ce magasin)
            transferts_in = StockMovement.objects.filter(
                product=stock.product,
                destination_store=stock.store,
                movement_type='transfer',
                is_active=True
            ).aggregate(total=Sum('quantity'))['total'] or Decimal('0')
            
            stock_theorique = entrees - sorties - transferts_out + transferts_in
            stock_actuel = stock.quantity
            
            difference = stock_actuel - stock_theorique
            
            if abs(difference) > Decimal('0.01'):  # Tolérance pour les arrondis
                issue = {
                    'stock': stock,
                    'product': stock.product.name,
                    'product_id': stock.product.id,
                    'store': stock.store.name,
                    'store_id': stock.store.id,
                    'stock_actuel': float(stock_actuel),
                    'stock_theorique': float(stock_theorique),
                    'difference': float(difference),
                    'entrees': float(entrees),
                    'sorties': float(sorties),
                    'transferts_out': float(transferts_out),
                    'transferts_in': float(transferts_in),
                }
                issues_found.append(issue)
        
        # 3. Afficher les problèmes trouvés
        if issues_found:
            self.stdout.write(self.style.ERROR(f"[ERREUR] {len(issues_found)} INCOHÉRENCE(S) DÉTECTÉE(S):\n"))
            for i, issue in enumerate(issues_found, 1):
                self.stdout.write(f"{i}. {issue['product']} - {issue['store']}")
                self.stdout.write(f"   Stock actuel en BD: {issue['stock_actuel']}")
                self.stdout.write(f"   Stock théorique (calculé): {issue['stock_theorique']}")
                self.stdout.write(self.style.WARNING(f"   Différence: {issue['difference']:+.2f}"))
                self.stdout.write(f"   Détails: Entrées={issue['entrees']}, Sorties={issue['sorties']}, "
                      f"Transferts Out={issue['transferts_out']}, Transferts In={issue['transferts_in']}")
                self.stdout.write("")
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Aucune incohérence détectée! Tous les stocks sont cohérents.\n"))
        
        # 4. Vérifier s'il y a des mouvements avec receipt_number inactifs
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("VÉRIFICATION DES BONS D'ENTRÉE SUPPRIMÉS")
        self.stdout.write("=" * 80 + "\n")
        
        inactive_receipts = StockMovement.objects.filter(
            is_active=False,
            receipt_number__isnull=False
        ).values('receipt_number').distinct()
        
        if inactive_receipts:
            self.stdout.write("📋 Bons d'entrée supprimés:")
            for receipt in inactive_receipts:
                receipt_num = receipt['receipt_number']
                movements = StockMovement.objects.filter(
                    receipt_number=receipt_num,
                    is_active=False
                )
                total_qty = movements.aggregate(total=Sum('quantity'))['total'] or 0
                self.stdout.write(f"   - {receipt_num}: {movements.count()} mouvement(s), Total quantité: {total_qty}")
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Aucun bon d'entrée supprimé.\n"))
        
        # 5. Correction si demandée
        if options['fix'] and issues_found:
            self.fix_issues(issues_found)
        elif options['fix'] and not issues_found:
            self.stdout.write(self.style.SUCCESS("\n[OK] Aucune correction nécessaire - Tous les stocks sont déjà cohérents!\n"))
        elif issues_found:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("[INFO] POUR CORRIGER LES INCOHÉRENCES"))
            self.stdout.write("=" * 80)
            self.stdout.write("\nExécutez la commande suivante:")
            self.stdout.write(self.style.SUCCESS("    python manage.py verify_stock --fix"))
            self.stdout.write("")

    def fix_issues(self, issues):
        """Corrige les incohérences de stock."""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("CORRECTION DES INCOHÉRENCES"))
        self.stdout.write("=" * 80 + "\n")
        
        self.stdout.write(f"[ATTENTION]  Correction de {len(issues)} stock(s)...")
        self.stdout.write("   Les stocks en base de données seront mis à jour avec les valeurs calculées.\n")
        
        corrected = 0
        for issue in issues:
            try:
                stock = issue['stock']
                old_quantity = stock.quantity
                new_quantity = Decimal(str(issue['stock_theorique']))
                
                stock.quantity = new_quantity
                stock.save()
                
                self.stdout.write(self.style.SUCCESS(f"✓ {issue['product']} - {issue['store']}"))
                self.stdout.write(f"  Ancien stock: {old_quantity}")
                self.stdout.write(f"  Nouveau stock: {new_quantity}")
                self.stdout.write(f"  Correction: {new_quantity - old_quantity:+.2f}\n")
                
                corrected += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Erreur lors de la correction de {issue['product']} - {issue['store']}: {e}\n"))
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"[OK] {corrected}/{len(issues)} stock(s) corrigé(s) avec succès!"))
        self.stdout.write("=" * 80 + "\n")
