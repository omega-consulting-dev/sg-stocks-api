#!/usr/bin/env python
"""
Script de migration des domaines tenants : *.app.sg-stocks.com → *.sg-stocks.com

Ajoute automatiquement le domaine {tenant}.sg-stocks.com pour tous les tenants existants
et le marque comme domaine principal.

Usage:
    python migrate_tenant_domains.py
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.prod')
django.setup()

from apps.tenants.models import Company, Domain


def migrate_tenant_domains():
    """
    Pour chaque tenant, ajoute le domaine {schema_name}.sg-stocks.com s'il n'existe pas
    et le marque comme domaine principal.
    """
    tenants = Company.objects.exclude(schema_name='public')
    
    print(f"🔍 Trouvé {tenants.count()} tenant(s) à migrer...")
    
    for tenant in tenants:
        new_domain = f"{tenant.schema_name}.sg-stocks.com"
        
        # Vérifier si le domaine existe déjà
        if Domain.objects.filter(domain=new_domain).exists():
            print(f"  ✓ {tenant.name} ({tenant.schema_name}) : {new_domain} existe déjà")
        else:
            # Créer le nouveau domaine principal
            Domain.objects.create(
                domain=new_domain,
                tenant=tenant,
                is_primary=True
            )
            print(f"  ✅ {tenant.name} ({tenant.schema_name}) : Créé {new_domain}")
            
            # Mettre à jour les anciens domaines pour ne plus être primary
            Domain.objects.filter(
                tenant=tenant
            ).exclude(
                domain=new_domain
            ).update(is_primary=False)
    
    print("\n✅ Migration terminée !")
    print("\nDomaines par tenant :")
    for tenant in tenants:
        domains = Domain.objects.filter(tenant=tenant)
        print(f"\n  {tenant.name} ({tenant.schema_name}) :")
        for d in domains:
            primary = " [PRIMARY]" if d.is_primary else ""
            print(f"    - {d.domain}{primary}")


if __name__ == '__main__':
    migrate_tenant_domains()
