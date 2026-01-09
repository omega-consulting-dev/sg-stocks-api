import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.tenants.models import Company, Domain
from apps.accounts.models import User
from django_tenants.utils import schema_context

# Rechercher le tenant AGRI BIO
tenant = Company.objects.filter(name__icontains='AGRI BIO').first()

if tenant:
    print("=" * 60)
    print("INFORMATIONS DU TENANT - AGRI BIO FUTURE SARL")
    print("=" * 60)
    print(f"Nom complet     : {tenant.name}")
    
    # Récupérer le domaine
    domain = Domain.objects.filter(tenant=tenant).first()
    if domain:
        print(f"Domaine         : {domain.domain}")
    
    print(f"Schema          : {tenant.schema_name}")
    print(f"Email           : {tenant.email}")
    print(f"Actif           : {'Oui' if tenant.is_active else 'Non'}")
    print(f"Plan            : {tenant.plan}")
    print()
    
    # Récupérer les utilisateurs de ce tenant
    with schema_context(tenant.schema_name):
        users = User.objects.all()[:10]
        
        if users.exists():
            print("=" * 60)
            print("UTILISATEURS DU TENANT")
            print("=" * 60)
            for user in users:
                print(f"\nUsername       : {user.username}")
                print(f"Email          : {user.email}")
                print(f"Nom complet    : {user.first_name} {user.last_name}")
                print(f"Staff          : {'Oui' if user.is_staff else 'Non'}")
                print(f"Superuser      : {'Oui' if user.is_superuser else 'Non'}")
                print(f"Actif          : {'Oui' if user.is_active else 'Non'}")
                print("-" * 60)
        else:
            print("Aucun utilisateur trouvé pour ce tenant")
else:
    print("Tenant 'AGRI BIO FUTURE SARL' non trouvé")
