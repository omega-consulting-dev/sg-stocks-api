#!/usr/bin/env python
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.test import RequestFactory
from core.views_field_config import FieldConfigurationViewSet
from apps.accounts.models import User

# Créer une requête factice
factory = RequestFactory()
request = factory.get('/api/v1/core/field-configurations/')

# Simuler un utilisateur authentifié
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()

request.user = user

# Appeler la vue
viewset = FieldConfigurationViewSet.as_view({'get': 'list'})
response = viewset(request)

print(f"Status Code: {response.status_code}")
print(f"Nombre de configurations: {len(response.data)}")
print("\nPremières configurations:")
for config in response.data[:3]:
    print(f"  - {config['form_name']}: {config['field_name']} ({config['field_label']})")
