"""
Commande pour mettre à jour les prix des entreprises selon leur plan.
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from apps.tenants.models import Company


class Command(BaseCommand):
    help = 'Met à jour les prix mensuels des entreprises selon leur plan'

    def handle(self, *args, **options):
        self.stdout.write('💰 Mise à jour des prix des entreprises...\n')
        
        # Définir les prix selon les plans
        prices = {
            'starter': Decimal('15000.00'),
            'business': Decimal('40000.00'),
            'enterprise': Decimal('60000.00'),
        }
        
        updated_count = 0
        
        for company in Company.objects.all():
            # Mettre à jour si le prix est à 0 ou ne correspond pas au plan
            expected_price = prices.get(company.plan, Decimal('15000.00'))
            
            if company.monthly_price != expected_price:
                old_price = company.monthly_price
                company.monthly_price = expected_price
                company.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] {company.name} ({company.plan}): {old_price} XAF -> {expected_price} XAF'
                    )
                )
                updated_count += 1
        
        # Résumé
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'[OK] {updated_count} entreprise(s) mise(s) à jour'))
        self.stdout.write('='*60)
