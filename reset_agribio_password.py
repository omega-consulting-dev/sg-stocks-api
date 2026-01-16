import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.tenants.models import Company
from apps.accounts.models import User
from django_tenants.utils import schema_context

# Rechercher le tenant AGRI BIO
tenant = Company.objects.filter(name__icontains='AGRI BIO').first()

if tenant:
    with schema_context(tenant.schema_name):
        # Trouver l'utilisateur admin
        user = User.objects.filter(email='admin@agribio.com').first()
        
        if user:
            # Définir un nouveau mot de passe
            new_password = 'Admin@2026'
            user.set_password(new_password)
            user.save()
            
            print("=" * 60)
            print("MOT DE PASSE RÉINITIALISÉ AVEC SUCCÈS")
            print("=" * 60)
            print(f"Email        : {user.email}")
            print(f"Username     : {user.username}")
            print(f"Nouveau MDP  : {new_password}")
            print("=" * 60)
            print("\n[ATTENTION]  Changez ce mot de passe après la première connexion")
        else:
            print("Utilisateur admin@agribio.com non trouvé")
else:
    print("Tenant AGRI BIO non trouvé")
