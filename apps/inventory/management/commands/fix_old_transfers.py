"""
Management command pour corriger les anciens transferts.
Crée les StockMovement manquants pour les transferts validés.

Usage:
    python manage.py fix_old_transfers
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context, get_tenant_model
from apps.inventory.models import StockTransfer, StockMovement, Stock


class Command(BaseCommand):
    help = 'Crée les StockMovement manquants pour les anciens transferts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Schema name du tenant (ex: agribio, santa). Si non spécifié, traite tous les tenants.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mode simulation: affiche ce qui serait fait sans modifier la base',
        )

    def handle(self, *args, **options):
        tenant_name = options.get('tenant')
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠ MODE SIMULATION - Aucune modification ne sera effectuée\n'))
        
        TenantModel = get_tenant_model()
        
        # Obtenir les tenants à traiter
        if tenant_name:
            tenants = TenantModel.objects.filter(schema_name=tenant_name)
            if not tenants.exists():
                self.stdout.write(self.style.ERROR(f'Tenant "{tenant_name}" non trouvé'))
                return
        else:
            # Exclure le tenant public
            tenants = TenantModel.objects.exclude(schema_name='public')
        
        total_fixed = 0
        total_skipped = 0
        total_errors = 0
        
        for tenant in tenants:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.SUCCESS(f'TENANT: {tenant.schema_name} ({tenant.name})'))
            self.stdout.write('=' * 80)
            
            with schema_context(tenant.schema_name):
                fixed, skipped, errors = self.fix_transfers_for_tenant(dry_run)
                total_fixed += fixed
                total_skipped += skipped
                total_errors += errors
        
        # Résumé global
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('RÉSUMÉ GLOBAL'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'✓ Transferts corrigés: {total_fixed}')
        self.stdout.write(f'⊘ Transferts déjà OK: {total_skipped}')
        self.stdout.write(f'✗ Erreurs: {total_errors}')
        self.stdout.write('=' * 80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠ MODE SIMULATION - Pour appliquer les modifications, relancez sans --dry-run\n'))
        elif total_fixed > 0:
            self.stdout.write(self.style.SUCCESS('\n✓ Les anciens transferts apparaissent maintenant dans les mouvements!\n'))

    def fix_transfers_for_tenant(self, dry_run=False):
        """Corriger les transferts pour le tenant courant."""
        
        # Trouver tous les transferts validés sans StockMovement
        transfers = StockTransfer.objects.filter(
            status__in=['in_transit', 'received']
        ).select_related('source_store', 'destination_store').prefetch_related('lines__product')
        
        self.stdout.write(f'\n✓ Trouvé {transfers.count()} transferts en transit ou reçus')
        
        fixed_count = 0
        skipped_count = 0
        error_count = 0
        
        for transfer in transfers:
            # Vérifier si des StockMovement existent déjà
            existing_movements = StockMovement.objects.filter(
                reference=transfer.transfer_number,
                movement_type='transfer'
            ).count()
            
            if existing_movements > 0:
                self.stdout.write(f'  ⊘ {transfer.transfer_number}: {existing_movements} StockMovement déjà existants')
                skipped_count += 1
                continue
            
            self.stdout.write(f'\n  -> {transfer.transfer_number}')
            self.stdout.write(f'     Source: {transfer.source_store.name} -> Dest: {transfer.destination_store.name}')
            self.stdout.write(f'     Date: {transfer.transfer_date}, Status: {transfer.status}')
            
            if dry_run:
                # Mode simulation
                for line in transfer.lines.all():
                    quantity = line.quantity_sent or line.quantity_requested or 0
                    if quantity > 0:
                        self.stdout.write(self.style.WARNING(
                            f'     [SIMULATION] Créerait StockMovement: {line.product.name}, Qté: {quantity}'
                        ))
                fixed_count += 1
                continue
            
            # Mode réel
            try:
                with transaction.atomic():
                    movements_created = 0
                    for line in transfer.lines.all():
                        quantity = line.quantity_sent or line.quantity_requested or 0
                        
                        if quantity <= 0:
                            continue
                        
                        # Créer le StockMovement
                        movement = StockMovement.objects.create(
                            product=line.product,
                            store=transfer.source_store,
                            destination_store=transfer.destination_store,
                            movement_type='transfer',
                            quantity=quantity,
                            reference=transfer.transfer_number,
                            notes=f'Transfert vers {transfer.destination_store.name}' + (f' - {transfer.notes}' if transfer.notes else ''),
                            date=transfer.transfer_date,
                            created_by=transfer.validated_by or transfer.created_by
                        )
                        movements_created += 1
                        
                        self.stdout.write(f'     + {line.product.name}: {quantity} (StockMovement #{movement.id})')
                    
                    if movements_created > 0:
                        fixed_count += 1
                        self.stdout.write(self.style.SUCCESS(f'     ✓ {movements_created} StockMovement(s) créé(s)'))
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'     ✗ ERREUR: {str(e)}'))
        
        return fixed_count, skipped_count, error_count
