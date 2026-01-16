#!/usr/bin/env python
"""
Script pour créer un utilisateur admin pour le tenant saker
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from apps.accounts.models import User, Role

def create_saker_admin():
    """Crée un utilisateur admin pour le tenant saker"""
    try:
        print("=" * 60)
        print("👤 CRÉATION D'UN UTILISATEUR ADMIN POUR SAKER")
        print("=" * 60)
        
        with schema_context('saker'):
            # Créer ou récupérer le rôle super_admin
            role, created = Role.objects.get_or_create(
                name='super_admin',
                defaults={
                    'display_name': 'Super Administrateur',
                    'description': 'Administrateur avec tous les droits',
                    'can_manage_users': True,
                    'can_manage_products': True,
                    'can_view_products': True,
                    'can_manage_categories': True,
                    'can_view_categories': True,
                    'can_manage_services': True,
                    'can_view_services': True,
                    'can_manage_inventory': True,
                    'can_view_inventory': True,
                    'can_manage_sales': True,
                    'can_manage_customers': True,
                    'can_manage_suppliers': True,
                    'can_manage_cashbox': True,
                    'can_manage_loans': True,
                    'can_manage_expenses': True,
                    'can_view_analytics': True,
                }
            )
            
            if created:
                print(f"✅ Rôle '{role.display_name}' créé")
            else:
                print(f"ℹ️  Rôle '{role.display_name}' existe déjà")
            
            # Vérifier si un admin existe déjà
            existing_admin = User.objects.filter(username='admin').first()
            
            if existing_admin:
                print("⚠️  Un utilisateur 'admin' existe déjà.")
                reset = input("Voulez-vous réinitialiser le mot de passe? (oui/non): ")
                if reset.lower() == 'oui':
                    existing_admin.set_password('admin123')
                    existing_admin.role = role
                    existing_admin.save()
                    print("✅ Mot de passe réinitialisé!")
                    print("\n📌 Informations de connexion:")
                    print(f"   - Username: admin")
                    print(f"   - Password: admin123")
                    print(f"   - Domaine: saker.localhost:8000")
                return
            
            # Créer l'utilisateur admin
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@saker.com',
                password='admin123',
                first_name='Admin',
                last_name='Saker',
                role=role,
                is_staff=True,
                is_superuser=True,
                is_active=True
            )
            
            print("✅ Utilisateur admin créé avec succès!")
            print("\n📌 Informations de connexion:")
            print(f"   - Username: {admin_user.username}")
            print(f"   - Email: {admin_user.email}")
            print(f"   - Password: admin123")
            print(f"   - Role: {admin_user.role}")
            print(f"   - Domaine: saker.localhost:8000")
            print("\n⚠️  N'oubliez pas de changer le mot de passe après la première connexion!")
            
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_saker_admin()
