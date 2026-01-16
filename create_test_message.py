#!/usr/bin/env python
"""Script pour créer un message de contact de test."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django_tenants.utils import schema_context
from apps.main.models_contact import ContactMessage

with schema_context('public'):
    # Créer un message de test
    message = ContactMessage.objects.create(
        first_name='Jean',
        last_name='Dupont',
        email='jean.dupont@example.com',
        phone='+237 690 000 000',
        message='Bonjour, je suis intéressé par votre solution de gestion de stock. Pouvez-vous me donner plus d\'informations sur les tarifs et les fonctionnalités disponibles ? Merci.',
        status='new'
    )
    
    print('[OK] Message de test créé avec succès!')
    print(f'   ID: {message.id}')
    print(f'   De: {message.first_name} {message.last_name}')
    print(f'   Email: {message.email}')
    print(f'   Status: {message.status}')
    print()
    print('📧 Rechargez la page AdminSgStock pour voir le message!')
