"""
Script to create super_admin role and assign it to superusers in tenant context.
Run with: python setup_admin_role.py
"""

import os
import sys
import django

# Add the project directory to Python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Setup Django - use the correct settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import tenant_context
from apps.tenants.models import Company
from apps.accounts.models import User, Role

print("=== Starting role setup ===\n")

# Get all tenants (exclude public schema)
tenants = Company.objects.exclude(schema_name='public')
print(f"Found {tenants.count()} tenant(s)\n")

for tenant in tenants:
    print(f"Processing tenant: {tenant.schema_name} ({tenant.name})")
    
    with tenant_context(tenant):
        # Create or update super_admin role
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
            print(f"  ✓ Created super_admin role")
        else:
            # Update permissions
            updated = False
            if not super_admin_role.can_manage_products:
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
                updated = True
            print(f"  ✓ Super_admin role {'updated' if updated else 'already exists'}")
        
        # Assign to all superusers
        all_superusers = User.objects.filter(is_superuser=True)
        print(f"  Found {all_superusers.count()} superuser(s)")
        
        for user in all_superusers:
            if not user.role:
                user.role = super_admin_role
                user.is_collaborator = True
                user.save()
                print(f"  ✓ Assigned role to: {user.username} ({user.email})")
            else:
                print(f"  • {user.username} already has role: {user.role.name}")
    
    print()

print("=== Done! ===")
print("\nAll superusers now have the super_admin role.")
print("You can now restart your server and login without permission issues.")

