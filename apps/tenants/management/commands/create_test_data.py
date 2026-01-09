"""
Command pour créer des données de test pour le SuperAdmin.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random

from apps.tenants.models import Company, CompanyBilling, AuditLog, SupportTicket


class Command(BaseCommand):
    help = 'Create test data for SuperAdmin interface'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating test data...')
        
        # Mettre à jour quelques entreprises avec des données réalistes
        companies = Company.objects.all()
        
        if not companies:
            self.stdout.write(self.style.WARNING('No companies found. Please create some tenants first.'))
            return
        
        for i, company in enumerate(companies):
            # Mettre à jour les infos de base
            company.monthly_price = Decimal(random.choice(['15000', '40000', '60000']))
            company.subscription_end_date = timezone.now().date() + timedelta(days=random.randint(5, 365))
            company.billing_email = f'billing-{company.schema_name}@example.com'
            
            # Quelques entreprises suspendues
            if i % 5 == 0:
                company.is_suspended = True
                company.suspension_reason = "Paiement en retard"
            
            company.save()
            
            # Créer des factures
            for month_offset in range(1, 4):
                invoice_date = timezone.now().date() - timedelta(days=month_offset * 30)
                due_date = invoice_date + timedelta(days=30)
                
                status = 'paid'
                payment_date = due_date + timedelta(days=random.randint(-5, 10))
                
                # Quelques factures en retard
                if random.random() < 0.2:
                    status = 'pending'
                    payment_date = None
                
                billing = CompanyBilling.objects.create(
                    company=company,
                    invoice_number=f'INV-{company.id}-{invoice_date.strftime("%Y%m")}',
                    invoice_date=invoice_date,
                    due_date=due_date,
                    amount=company.monthly_price,
                    tax_amount=company.monthly_price * Decimal('0.1925'),
                    total_amount=company.monthly_price * Decimal('1.1925'),
                    status=status,
                    payment_date=payment_date,
                    payment_method='bank_transfer' if status == 'paid' else ''
                )
                
                self.stdout.write(f'Created billing {billing.invoice_number}')
            
            # Créer des logs d'audit
            actions = [
                ('company_update', 'Updated company settings'),
                ('plan_change', f'Changed plan to {company.plan}'),
                ('user_login', 'Admin user logged in'),
                ('data_export', 'Exported sales data'),
                ('backup_create', 'Created database backup')
            ]
            
            for j in range(5):
                action_type, description = random.choice(actions)
                
                AuditLog.objects.create(
                    company=company,
                    admin_user=f'admin-{company.schema_name}',
                    action_type=action_type,
                    action_description=f'{description} for {company.name}',
                    resource_type='company',
                    resource_id=str(company.id),
                    timestamp=timezone.now() - timedelta(days=random.randint(0, 30))
                )
            
            # Créer des tickets de support
            tickets_data = [
                ('Cannot login to dashboard', 'high', 'Login issues after password reset'),
                ('Slow performance', 'normal', 'Dashboard loading very slowly'),
                ('Missing sales data', 'high', 'Sales from last week not showing'),
                ('Feature request', 'low', 'Can we add inventory alerts?'),
                ('Payment failed', 'urgent', 'Monthly payment was declined')
            ]
            
            # 70% de chance d'avoir des tickets
            if random.random() < 0.7:
                title, priority, description = random.choice(tickets_data)
                
                status = random.choice(['open', 'in_progress', 'resolved'])
                
                ticket = SupportTicket.objects.create(
                    company=company,
                    title=title,
                    description=description,
                    priority=priority,
                    status=status,
                    customer_name=f'Admin {company.name}',
                    customer_email=company.email,
                    assigned_to='support-agent' if status != 'open' else '',
                    created_at=timezone.now() - timedelta(days=random.randint(0, 14))
                )
                
                if status == 'resolved':
                    ticket.resolved_at = ticket.created_at + timedelta(days=random.randint(1, 5))
                    ticket.save()
                
                self.stdout.write(f'Created ticket {ticket.ticket_number}')
        
        self.stdout.write(
            self.style.SUCCESS('Test data created successfully!')
        )
        
        # Afficher un résumé
        total_companies = Company.objects.count()
        total_billings = CompanyBilling.objects.count()
        total_logs = AuditLog.objects.count()
        total_tickets = SupportTicket.objects.count()
        
        self.stdout.write(f'Summary:')
        self.stdout.write(f'  Companies: {total_companies}')
        self.stdout.write(f'  Billings: {total_billings}')
        self.stdout.write(f'  Audit logs: {total_logs}')
        self.stdout.write(f'  Support tickets: {total_tickets}')