"""
Commande Django pour vérifier et suspendre les tenants avec abonnements expirés.
Cette commande doit être exécutée régulièrement (ex: cron quotidien).

Usage:
    python manage.py check_expired_subscriptions
    python manage.py check_expired_subscriptions --suspend  # Pour suspendre automatiquement
    python manage.py check_expired_subscriptions --notify   # Pour envoyer des notifications
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.tenants.models import Company
from datetime import timedelta


class Command(BaseCommand):
    help = 'Vérifie les abonnements expirés et peut suspendre automatiquement les comptes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--suspend',
            action='store_true',
            help='Suspendre automatiquement les comptes expirés',
        )
        parser.add_argument(
            '--notify',
            action='store_true',
            help='Envoyer des notifications aux comptes qui vont expirer',
        )
        parser.add_argument(
            '--notify-days',
            type=int,
            default=7,
            help='Nombre de jours avant expiration pour notifier (défaut: 7)',
        )
        parser.add_argument(
            '--grace-period',
            type=int,
            default=0,
            help='Période de grâce en jours après expiration avant suspension (défaut: 0)',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        suspend = options['suspend']
        notify = options['notify']
        notify_days = options['notify_days']
        grace_period = options['grace_period']
        
        self.stdout.write(self.style.SUCCESS(f'🔍 Vérification des abonnements au {today}'))
        
        # 1. Comptes expirés
        expired_tenants = Company.objects.filter(
            subscription_end_date__lt=today - timedelta(days=grace_period),
            is_active=True
        ).exclude(
            is_suspended=True
        )
        
        expired_count = expired_tenants.count()
        if expired_count > 0:
            self.stdout.write(self.style.WARNING(f'\n⚠️  {expired_count} tenant(s) avec abonnement expiré:'))
            
            for tenant in expired_tenants:
                days_expired = (today - tenant.subscription_end_date).days if tenant.subscription_end_date else 0
                self.stdout.write(
                    f'  - {tenant.name} ({tenant.schema_name}): '
                    f'expiré depuis {days_expired} jour(s) - '
                    f'Date d\'expiration: {tenant.subscription_end_date}'
                )
                
                if suspend:
                    tenant.is_suspended = True
                    tenant.suspension_reason = f'Abonnement expiré le {tenant.subscription_end_date}'
                    tenant.save()
                    self.stdout.write(self.style.ERROR(f'    ✓ Compte suspendu'))
                else:
                    self.stdout.write(f'    ℹ️  Utilisez --suspend pour suspendre automatiquement')
        else:
            self.stdout.write(self.style.SUCCESS('✓ Aucun tenant avec abonnement expiré'))
        
        # 2. Comptes qui vont expirer bientôt
        expiring_soon_tenants = Company.objects.filter(
            subscription_end_date__gte=today,
            subscription_end_date__lte=today + timedelta(days=notify_days),
            is_active=True,
            is_suspended=False
        )
        
        expiring_count = expiring_soon_tenants.count()
        if expiring_count > 0:
            self.stdout.write(
                self.style.WARNING(f'\n⏰ {expiring_count} tenant(s) dont l\'abonnement expire dans les {notify_days} prochains jours:')
            )
            
            for tenant in expiring_soon_tenants:
                days_remaining = (tenant.subscription_end_date - today).days if tenant.subscription_end_date else 0
                self.stdout.write(
                    f'  - {tenant.name} ({tenant.schema_name}): '
                    f'expire dans {days_remaining} jour(s) - '
                    f'Date d\'expiration: {tenant.subscription_end_date}'
                )
                
                if notify:
                    # TODO: Envoyer une notification email
                    # send_expiration_notification(tenant, days_remaining)
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Notification envoyée (TODO: implémenter l\'envoi d\'email)'))
                else:
                    self.stdout.write(f'    ℹ️  Utilisez --notify pour envoyer des notifications')
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Aucun tenant n\'expire dans les {notify_days} prochains jours'))
        
        # 3. Statistiques générales
        total_active = Company.objects.filter(is_active=True, is_suspended=False).count()
        total_suspended = Company.objects.filter(is_suspended=True).count()
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Statistiques:'))
        self.stdout.write(f'  - Tenants actifs: {total_active}')
        self.stdout.write(f'  - Tenants suspendus: {total_suspended}')
        self.stdout.write(f'  - Tenants expirés (non suspendus): {expired_count}')
        self.stdout.write(f'  - Tenants expirant bientôt: {expiring_count}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Vérification terminée'))
