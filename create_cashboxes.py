"""
Script pour créer automatiquement une caisse pour chaque point de vente.
Usage: python create_cashboxes.py
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.inventory.models import Store
from apps.cashbox.models import Cashbox
from django.db import connection


def create_cashboxes_for_tenant(tenant):
    """Créer les caisses manquantes pour un tenant."""
    connection.set_tenant(tenant)
    
    stores = Store.objects.all()
    created_count = 0
    
    print(f"\n📦 Tenant: {tenant.name} ({tenant.schema_name})")
    print(f"   Points de vente trouvés: {stores.count()}")
    
    for store in stores:
        # Vérifier si une caisse existe déjà pour ce store
        cashbox = Cashbox.objects.filter(store=store).first()
        
        if cashbox:
            if cashbox.is_active:
                print(f"   ✅ Caisse existante pour {store.name}: {cashbox.code} - {cashbox.name} (Active)")
            else:
                print(f"   ⚠️  Caisse existante pour {store.name}: {cashbox.code} - {cashbox.name} (Inactive)")
                # Activer la caisse
                cashbox.is_active = True
                cashbox.save()
                print(f"      → Caisse activée!")
        else:
            # Créer une nouvelle caisse
            cashbox = Cashbox.objects.create(
                name=f"Caisse {store.name}",
                code=f"CAISSE-{store.code}",
                store=store,
                current_balance=0,
                is_active=True
            )
            created_count += 1
            print(f"   ✨ Nouvelle caisse créée pour {store.name}: {cashbox.code}")
    
    return created_count


def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("🏦 Création automatique des caisses pour tous les tenants")
    print("=" * 60)
    
    # Importer le modèle Tenant
    from django_tenants.utils import get_tenant_model, get_public_schema_name
    
    Tenant = get_tenant_model()
    public_schema_name = get_public_schema_name()
    
    # Récupérer tous les tenants sauf le schéma public
    tenants = Tenant.objects.exclude(schema_name=public_schema_name)
    
    total_created = 0
    
    for tenant in tenants:
        try:
            created = create_cashboxes_for_tenant(tenant)
            total_created += created
        except Exception as e:
            print(f"   ❌ Erreur pour {tenant.name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ Terminé! {total_created} nouvelle(s) caisse(s) créée(s)")
    print("=" * 60)


if __name__ == '__main__':
    main()
