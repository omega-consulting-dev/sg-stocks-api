#!/usr/bin/env python
"""
Script pour vérifier les données de l'utilisateur charli
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from apps.accounts.models import User

def check_charli_user():
    schema_name = 'saker'
    connection.set_schema(schema_name)
    
    print(f"\n📋 Vérification de l'utilisateur charli dans le tenant: {schema_name}\n")
    
    try:
        user = User.objects.get(username='charli')
        
        print(f"👤 Utilisateur: {user.username}")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Prénom: {user.first_name or 'N/A'}")
        print(f"   Nom: {user.last_name or 'N/A'}")
        print(f"   Employee ID: {user.employee_id or 'N/A'}")
        print(f"\n🎭 ROLE:")
        print(f"   Role: {user.role}")
        print(f"   Role ID: {user.role.id if user.role else 'N/A'}")
        print(f"   Role Name: {user.role.display_name if user.role else 'N/A'}")
        
        print(f"\n🏪 STORES:")
        stores = user.assigned_stores.all()
        if stores.exists():
            for store in stores:
                print(f"   - {store.name} (ID: {store.id})")
        else:
            print(f"   Aucun store assigné")
        
        print(f"\n✅ Actif: {user.is_active}")
        
    except User.DoesNotExist:
        print("\n❌ Utilisateur 'charli' non trouvé")

if __name__ == '__main__':
    check_charli_user()
