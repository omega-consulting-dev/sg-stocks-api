"""
Management command to synchronize plan limits for all tenants.
This command applies the correct limits based on each tenant's plan.

Usage:
    python manage.py sync_plan_limits
"""

from django.core.management.base import BaseCommand
from apps.tenants.models import Company


class Command(BaseCommand):
    help = 'Synchronize plan limits for all tenants based on their current plan'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually making changes',
        )
        parser.add_argument(
            '--tenant',
            type=str,
            help='Sync limits for a specific tenant by schema_name',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_tenant = options.get('tenant')

        self.stdout.write(self.style.SUCCESS('=== Synchronisation des limites de plan ==='))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODE DRY-RUN: Aucune modification ne sera effectuée'))
        
        # Filtrer les tenants
        if specific_tenant:
            tenants = Company.objects.filter(schema_name=specific_tenant)
            if not tenants.exists():
                self.stdout.write(self.style.ERROR(f'Tenant {specific_tenant} introuvable'))
                return
        else:
            tenants = Company.objects.exclude(schema_name='public')
        
        total_synced = 0
        total_skipped = 0
        
        for tenant in tenants:
            self.stdout.write(f'\nTenant: {tenant.name} ({tenant.schema_name})')
            self.stdout.write(f'  Plan actuel: {tenant.plan}')
            
            # Sauvegarder les valeurs actuelles
            old_values = {
                'max_users': tenant.max_users,
                'max_stores': tenant.max_stores,
                'max_warehouses': tenant.max_warehouses,
                'max_products': tenant.max_products,
                'max_storage_mb': tenant.max_storage_mb,
                'feature_services': tenant.feature_services,
                'feature_multi_store': tenant.feature_multi_store,
                'feature_loans': tenant.feature_loans,
                'feature_advanced_analytics': tenant.feature_advanced_analytics,
                'feature_api_access': tenant.feature_api_access,
            }
            
            # Appliquer les nouvelles limites
            tenant.apply_plan_limits()
            
            # Comparer les changements
            changes = []
            if old_values['max_users'] != tenant.max_users:
                changes.append(f"max_users: {old_values['max_users']} → {tenant.max_users}")
            if old_values['max_stores'] != tenant.max_stores:
                changes.append(f"max_stores: {old_values['max_stores']} → {tenant.max_stores}")
            if old_values['max_warehouses'] != tenant.max_warehouses:
                changes.append(f"max_warehouses: {old_values['max_warehouses']} → {tenant.max_warehouses}")
            if old_values['max_products'] != tenant.max_products:
                changes.append(f"max_products: {old_values['max_products']} → {tenant.max_products}")
            if old_values['max_storage_mb'] != tenant.max_storage_mb:
                changes.append(f"max_storage_mb: {old_values['max_storage_mb']} → {tenant.max_storage_mb}")
            if old_values['feature_services'] != tenant.feature_services:
                changes.append(f"feature_services: {old_values['feature_services']} → {tenant.feature_services}")
            if old_values['feature_multi_store'] != tenant.feature_multi_store:
                changes.append(f"feature_multi_store: {old_values['feature_multi_store']} → {tenant.feature_multi_store}")
            if old_values['feature_loans'] != tenant.feature_loans:
                changes.append(f"feature_loans: {old_values['feature_loans']} → {tenant.feature_loans}")
            if old_values['feature_advanced_analytics'] != tenant.feature_advanced_analytics:
                changes.append(f"feature_advanced_analytics: {old_values['feature_advanced_analytics']} → {tenant.feature_advanced_analytics}")
            if old_values['feature_api_access'] != tenant.feature_api_access:
                changes.append(f"feature_api_access: {old_values['feature_api_access']} → {tenant.feature_api_access}")
            
            if changes:
                self.stdout.write(self.style.WARNING("  Changements détectés:"))
                for change in changes:
                    self.stdout.write(f"    - {change}")
                
                if not dry_run:
                    tenant.save()
                    self.stdout.write(self.style.SUCCESS("  ✓ Limites synchronisées"))
                    total_synced += 1
                else:
                    self.stdout.write(self.style.WARNING("  [DRY-RUN] Limites non sauvegardées"))
                    total_synced += 1
            else:
                self.stdout.write(self.style.SUCCESS("  ✓ Déjà à jour"))
                total_skipped += 1
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Résumé:'))
        self.stdout.write(f'  - Tenants synchronisés: {total_synced}')
        self.stdout.write(f'  - Tenants déjà à jour: {total_skipped}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODE DRY-RUN: Exécutez sans --dry-run pour appliquer les changements'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Synchronisation terminée avec succès'))
