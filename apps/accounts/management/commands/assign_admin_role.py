"""
Management command to assign super_admin role to superusers.
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import User, Role


class Command(BaseCommand):
    help = 'Assign super_admin role to all superusers who don\'t have a role'

    def handle(self, *args, **options):
        # Get or create super_admin role
        super_admin_role, created = Role.objects.get_or_create(
            name='super_admin',
            defaults={
                'display_name': 'Super Administrateur',
                'description': 'Accès complet à toutes les fonctionnalités',
                'can_manage_users': True,
                'can_manage_products': True,
                'can_manage_services': True,
                'can_manage_inventory': True,
                'can_manage_sales': True,
                'can_manage_customers': True,
                'can_manage_suppliers': True,
                'can_manage_cashbox': True,
                'can_manage_loans': True,
                'can_manage_expenses': True,
                'can_view_analytics': True,
                'can_export_data': True,
                'access_scope': 'all',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created super_admin role'))
        else:
            # Update existing role to ensure all permissions are set
            super_admin_role.can_manage_users = True
            super_admin_role.can_manage_products = True
            super_admin_role.can_manage_services = True
            super_admin_role.can_manage_inventory = True
            super_admin_role.can_manage_sales = True
            super_admin_role.can_manage_customers = True
            super_admin_role.can_manage_suppliers = True
            super_admin_role.can_manage_cashbox = True
            super_admin_role.can_manage_loans = True
            super_admin_role.can_manage_expenses = True
            super_admin_role.can_view_analytics = True
            super_admin_role.can_export_data = True
            super_admin_role.access_scope = 'all'
            super_admin_role.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Updated super_admin role'))
        
        # Assign role to all superusers without a role
        superusers = User.objects.filter(is_superuser=True, role__isnull=True)
        count = 0
        
        for user in superusers:
            user.role = super_admin_role
            user.is_collaborator = True
            user.save()
            count += 1
            self.stdout.write(self.style.SUCCESS(f'✓ Assigned super_admin role to {user.username}'))
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No superusers found without a role'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully assigned super_admin role to {count} user(s)'))
