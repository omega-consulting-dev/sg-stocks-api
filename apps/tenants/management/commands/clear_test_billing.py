"""
Commande pour supprimer les données de test de facturation.
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import CompanyBilling


class Command(BaseCommand):
    help = 'Supprime toutes les factures de test'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmer la suppression',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('[ATTENTION]  Cette commande supprimera TOUTES les factures.')
            )
            self.stdout.write(
                self.style.WARNING('Pour confirmer, utilisez: python manage.py clear_test_billing --confirm')
            )
            return
        
        self.stdout.write('[SUPPRESSION]  Suppression des factures de test...\n')
        
        count = CompanyBilling.objects.count()
        CompanyBilling.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'[OK] {count} facture(s) supprimée(s)')
        )
