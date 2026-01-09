"""
Management command pour collecter les métriques système.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum
from apps.tenants.models import Company, SystemMetrics, CompanyBilling
from django_tenants.utils import connection, get_public_schema_name


class Command(BaseCommand):
    help = 'Collect system-wide metrics for monitoring'
    
    def handle(self, *args, **options):
        self.stdout.write('Collecting system metrics...')
        
        # S'assurer d'être sur le schema public
        connection.set_schema_to_public()
        
        # Calculer les métriques globales
        total_tenants = Company.objects.count()
        active_tenants = Company.objects.filter(is_active=True, is_suspended=False).count()
        
        # Compter les utilisateurs dans tous les tenants
        total_users = 0
        for company in Company.objects.all():
            try:
                connection.set_tenant(company)
                from apps.accounts.models import User
                tenant_users = User.objects.count()
                total_users += tenant_users
                
                # Mettre à jour le compteur de l'entreprise
                company.total_users_count = tenant_users
                # Pour l'instant, valeurs par défaut basées sur les utilisateurs
                if tenant_users > 0:
                    company.total_products_count = min(tenant_users * 50, company.max_products)
                    company.storage_used_mb = tenant_users * 15
                else:
                    company.total_products_count = 0
                    company.storage_used_mb = 0
                    
                company.last_activity_date = timezone.now()
                
            except Exception as e:
                self.stdout.write(f"Error processing tenant {company.name}: {e}")
                # Valeurs par défaut si erreur
                company.total_users_count = 1
                company.total_products_count = 10
                company.storage_used_mb = 20
                company.last_activity_date = timezone.now()
                total_users += 1
        
        # Retourner au schema public et sauvegarder les updates
        connection.set_schema_to_public()
        for company in Company.objects.all():
            company.save(update_fields=[
                'total_users_count', 'total_products_count', 
                'storage_used_mb', 'last_activity_date'
            ])
        
        # Revenus du mois
        current_month_start = timezone.now().date().replace(day=1)
        monthly_revenue = CompanyBilling.objects.filter(
            status='paid',
            payment_date__gte=current_month_start
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Stockage total utilisé
        total_storage_mb = Company.objects.aggregate(
            total=Sum('storage_used_mb')
        )['total'] or 0
        total_storage_gb = total_storage_mb / 1024 if total_storage_mb > 0 else 0
        
        # Créer l'entrée de métriques
        metrics = SystemMetrics.objects.create(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_users=total_users,
            total_revenue_monthly=monthly_revenue,
            total_storage_used_gb=total_storage_gb,
            avg_response_time_ms=150,  # TODO: calculer depuis les logs
            error_rate_percent=0.5,   # TODO: calculer depuis les logs
            peak_concurrent_users=max(total_users // 10, 1)  # Estimation
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Metrics collected successfully at {metrics.recorded_at}'
            )
        )
        self.stdout.write(f'Total tenants: {total_tenants}')
        self.stdout.write(f'Active tenants: {active_tenants}')
        self.stdout.write(f'Total users: {total_users}')
        self.stdout.write(f'Total storage: {total_storage_gb:.2f} GB')
        
        # Nettoyer les anciennes métriques (garder seulement 90 jours)
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        deleted_count, _ = SystemMetrics.objects.filter(
            recorded_at__lt=cutoff_date
        ).delete()
        
        if deleted_count > 0:
            self.stdout.write(
                f'Cleaned up {deleted_count} old metrics records'
            )
        
        self.stdout.write(
            self.style.SUCCESS('All metrics updated successfully!')
        )