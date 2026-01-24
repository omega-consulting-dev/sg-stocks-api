#!/usr/bin/env python
"""
Script pour supprimer et recréer le tenant saker
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.tenants.models import Company, Domain
from django.db import connection

def delete_saker_tenant():
    """Supprime le tenant saker et son schéma"""
    try:
        # Récupérer le tenant saker
        saker = Company.objects.filter(schema_name='saker').first()
        
        if not saker:
            print("❌ Le tenant 'saker' n'existe pas.")
            return False
            
        print(f"🔍 Tenant trouvé: {saker.name} (schéma: {saker.schema_name})")
        
        # Confirmation
        confirmation = input("⚠️  ATTENTION: Cette action supprimera TOUTES les données du tenant 'saker'. Continuer? (oui/non): ").strip().lower()
        if confirmation != 'oui':
            print("❌ Opération annulée.")
            return False
        
        # Supprimer le schéma (cela supprime automatiquement toutes les tables)
        print(f"🗑️  Suppression du schéma '{saker.schema_name}'...")
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS {saker.schema_name} CASCADE')
        
        # Supprimer l'enregistrement du tenant
        print(f"🗑️  Suppression de l'enregistrement du tenant...")
        saker.delete()
        
        print("✅ Tenant 'saker' supprimé avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_saker_tenant():
    """Crée un nouveau tenant saker"""
    try:
        print("\n📝 Création du nouveau tenant 'saker'...")
        
        # Créer le tenant
        tenant = Company.objects.create(
            schema_name='saker',
            name='Saker',
        )
        
        print(f"✅ Tenant créé: {tenant.name} (schéma: {tenant.schema_name})")
        
        # Créer le domaine
        domain = Domain.objects.create(
            domain='saker.localhost',
            tenant=tenant,
            is_primary=True
        )
        
        print(f"✅ Domaine créé: {domain.domain}")
        
        # Initialiser les configurations de champs
        print("\n📋 Initialisation des configurations de champs...")
        from django.core.management import call_command
        
        # Utiliser le tenant context pour créer les configurations
        from django_tenants.utils import schema_context
        
        with schema_context('saker'):
            # Vous pouvez ajouter ici l'initialisation des données par défaut
            # Par exemple, appeler initialize_field_configs pour ce tenant
            pass
        
        print("✅ Tenant 'saker' recréé avec succès!")
        print(f"\n📌 Informations du tenant:")
        print(f"   - Nom: {tenant.name}")
        print(f"   - Schéma: {tenant.schema_name}")
        print(f"   - Domaine: {domain.domain}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("🔄 SUPPRESSION ET RECRÉATION DU TENANT SAKER")
    print("=" * 60)
    
    # Étape 1: Supprimer le tenant existant
    if delete_saker_tenant():
        # Étape 2: Créer le nouveau tenant
        create_saker_tenant()
    else:
        print("\n❌ La suppression a échoué. Aucune création effectuée.")

if __name__ == '__main__':
    main()
