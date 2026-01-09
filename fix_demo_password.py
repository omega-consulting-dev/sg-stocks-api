"""
Script rapide pour changer le mot de passe du compte démo.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.base')
django.setup()

from django_tenants.utils import schema_context
from apps.accounts.models import User

print("=" * 80)
print("CHANGEMENT DU MOT DE PASSE DÉMO")
print("=" * 80)

with schema_context('demo'):
    demo_user = User.objects.filter(email='demo@sgstock.cm').first()
    
    if demo_user:
        # Changer le mot de passe pour respecter la contrainte de 8 caractères minimum
        demo_user.set_password('demo1234')
        demo_user.save()
        
        print("\n✅ Mot de passe mis à jour avec succès!")
        print(f"\n📌 Nouvelles informations de connexion:")
        print(f"   Email: demo@sgstock.cm")
        print(f"   Mot de passe: demo1234")
        print(f"\n   Accès: http://demo.localhost:5173")
    else:
        print("\n❌ Utilisateur démo non trouvé!")

print("\n" + "=" * 80)
