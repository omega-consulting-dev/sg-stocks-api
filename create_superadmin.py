#!/usr/bin/env python
"""Script simple pour créer un super admin."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.main.models import User

with schema_context('public'):
    email = 'admin@localhost'
    password = 'admin123'
    
    if not User.objects.filter(email=email).exists():
        user = User.objects.create_superuser(
            email=email,
            username='admin',
            password=password,
            first_name='Admin',
            last_name='System'
        )
        print(f'✅ Super admin créé avec succès!')
    else:
        user = User.objects.get(email=email)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        print(f'✅ Mot de passe réinitialisé avec succès!')
    
    print()
    print('📋 IDENTIFIANTS DE CONNEXION:')
    print(f'   Email    : {email}')
    print(f'   Password : {password}')
    print()
