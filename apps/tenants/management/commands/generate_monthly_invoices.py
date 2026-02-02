"""
Commande pour générer les factures mensuelles pour toutes les entreprises actives.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from apps.tenants.models import Company, CompanyBilling


class Command(BaseCommand):
    help = 'Génère les factures mensuelles pour toutes les entreprises actives'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='Mois à facturer (format: YYYY-MM). Par défaut: mois actuel',
        )

    def handle(self, *args, **options):
        self.stdout.write('🧾 Génération des factures mensuelles...\n')
        
        # Déterminer le mois à facturer
        if options['month']:
            year, month = map(int, options['month'].split('-'))
            invoice_date = timezone.datetime(year, month, 1).date()
        else:
            invoice_date = timezone.now().date().replace(day=1)
        
        due_date = invoice_date + timedelta(days=30)
        
        # Récupérer toutes les entreprises actives (sauf public)
        companies = Company.objects.filter(
            is_active=True
        ).exclude(schema_name='public')
        
        created_count = 0
        skipped_count = 0
        
        for company in companies:
            # Vérifier si une facture existe déjà pour ce mois
            invoice_number = f'INV-{company.id}-{invoice_date.strftime("%Y%m")}'
            
            if CompanyBilling.objects.filter(invoice_number=invoice_number).exists():
                self.stdout.write(
                    self.style.WARNING(f'[SKIP]  Facture déjà existante pour {company.name} ({invoice_number})')
                )
                skipped_count += 1
                continue
            
            # Calculer le montant selon le plan
            amount = company.monthly_price
            tax_amount = Decimal('0')  # Pas de TVA
            total_amount = amount  # Total = Montant HT
            
            # Créer la facture
            billing = CompanyBilling.objects.create(
                company=company,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                due_date=due_date,
                amount=amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                status='pending',
                notes=f'Facturation mensuelle - Plan {company.plan}'
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Facture créée: {billing.invoice_number} - {company.name} - {total_amount} XAF')
            )
            created_count += 1
        
        # Résumé
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'[OK] {created_count} facture(s) créée(s)'))
        self.stdout.write(self.style.WARNING(f'[SKIP]  {skipped_count} facture(s) déjà existante(s)'))
        self.stdout.write(f'📅 Mois facturé: {invoice_date.strftime("%B %Y")}')
        self.stdout.write('='*60)
