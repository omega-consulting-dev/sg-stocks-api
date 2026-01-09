import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.tenants.models import Company, Domain

# Rechercher le tenant AGRI BIO
tenant = Company.objects.filter(name__icontains='AGRI BIO').first()

if tenant:
    print("=" * 60)
    print("MODIFICATION DU DOMAINE AGRI BIO")
    print("=" * 60)
    
    # Récupérer le domaine actuel
    current_domain = Domain.objects.filter(tenant=tenant).first()
    
    if current_domain:
        print(f"Domaine actuel  : {current_domain.domain}")
        print(f"Is primary      : {current_domain.is_primary}")
        
        # Modifier le domaine vers localhost avec un sous-domaine unique
        new_domain_name = "agribio.localhost"
        current_domain.domain = new_domain_name
        current_domain.save()
        
        print(f"\n✅ Domaine modifié : {new_domain_name}")
        print("\nVous pouvez maintenant vous connecter via:")
        print(f"  URL: http://agribio.localhost:5173")
        print(f"  Email: admin@agribio.com")
        print(f"  Password: Admin@2026")
        print("\n⚠️  Note: Ajoutez cette ligne dans votre fichier hosts:")
        print("  127.0.0.1 agribio.localhost")
    else:
        print("❌ Aucun domaine trouvé pour ce tenant")
else:
    print("❌ Tenant AGRI BIO non trouvé")
