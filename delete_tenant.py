"""
Script pour supprimer un tenant et toutes ses données associées
Usage: python delete_tenant.py
"""

import os
import django
import sys

# Configuration Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from apps.tenants.models import Company, Domain

def list_tenants():
    """Affiche la liste de tous les tenants"""
    tenants = Company.objects.exclude(schema_name='public').order_by('-created_on')
    
    if not tenants.exists():
        print("❌ Aucun tenant trouvé (hors 'public')")
        return []
    
    print("\n📋 Liste des tenants :\n")
    print(f"{'ID':<5} {'Nom':<30} {'Schema':<25} {'Plan':<15} {'Créé le':<20}")
    print("-" * 100)
    
    for tenant in tenants:
        created = tenant.created_on.strftime('%d/%m/%Y %H:%M') if tenant.created_on else 'N/A'
        print(f"{tenant.id:<5} {tenant.name[:29]:<30} {tenant.schema_name[:24]:<25} {tenant.plan:<15} {created:<20}")
    
    return list(tenants)

def delete_tenant(tenant_id=None, schema_name=None):
    """Supprime un tenant et toutes ses données"""
    
    try:
        # Trouver le tenant
        if tenant_id:
            tenant = Company.objects.get(id=tenant_id)
        elif schema_name:
            tenant = Company.objects.get(schema_name=schema_name)
        else:
            print("❌ Veuillez fournir un ID ou un nom de schéma")
            return False
        
        # Vérification de sécurité
        if tenant.schema_name == 'public':
            print("❌ Impossible de supprimer le schema 'public' !")
            return False
        
        print(f"\n⚠️  Vous allez supprimer le tenant :")
        print(f"   Nom: {tenant.name}")
        print(f"   Schema: {tenant.schema_name}")
        print(f"   Plan: {tenant.plan}")
        
        confirmation = input("\n⚠️  Êtes-vous sûr de vouloir supprimer ce tenant ? (oui/non): ")
        
        if confirmation.lower() not in ['oui', 'yes', 'o', 'y']:
            print("❌ Suppression annulée")
            return False
        
        # 1. Supprimer les domaines associés
        domains = Domain.objects.filter(tenant=tenant)
        domain_count = domains.count()
        if domain_count > 0:
            print(f"\n🗑️  Suppression de {domain_count} domaine(s)...")
            domains.delete()
            print("   ✅ Domaines supprimés")
        
        # 2. Supprimer le schéma PostgreSQL
        print(f"\n🗑️  Suppression du schéma PostgreSQL '{tenant.schema_name}'...")
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{tenant.schema_name}" CASCADE;')
        print("   ✅ Schéma PostgreSQL supprimé")
        
        # 3. Supprimer le tenant de la table public.tenants_company
        print(f"\n🗑️  Suppression du tenant '{tenant.name}'...")
        tenant_name = tenant.name
        tenant.delete()
        print(f"   ✅ Tenant '{tenant_name}' supprimé")
        
        print("\n✅ Tenant supprimé avec succès !")
        return True
        
    except Company.DoesNotExist:
        print(f"❌ Tenant non trouvé")
        return False
    except Exception as e:
        print(f"\n❌ Erreur lors de la suppression: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def delete_last_tenant():
    """Supprime le dernier tenant créé"""
    try:
        last_tenant = Company.objects.exclude(schema_name='public').order_by('-created_on').first()
        
        if not last_tenant:
            print("❌ Aucun tenant trouvé")
            return False
        
        print(f"\n🔍 Dernier tenant créé :")
        print(f"   Nom: {last_tenant.name}")
        print(f"   Schema: {last_tenant.schema_name}")
        print(f"   Créé le: {last_tenant.created_on.strftime('%d/%m/%Y %H:%M')}")
        
        return delete_tenant(tenant_id=last_tenant.id)
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

def main():
    print("=" * 100)
    print("🗑️  SCRIPT DE SUPPRESSION DE TENANT")
    print("=" * 100)
    
    # Afficher la liste des tenants
    tenants = list_tenants()
    
    if not tenants:
        print("\n✅ Rien à supprimer")
        return
    
    print("\n📌 Options :")
    print("   1. Supprimer le dernier tenant créé")
    print("   2. Supprimer un tenant par ID")
    print("   3. Supprimer un tenant par nom de schéma")
    print("   4. Quitter")
    
    choice = input("\n👉 Votre choix (1-4): ").strip()
    
    if choice == '1':
        delete_last_tenant()
    
    elif choice == '2':
        try:
            tenant_id = int(input("\n👉 Entrez l'ID du tenant: ").strip())
            delete_tenant(tenant_id=tenant_id)
        except ValueError:
            print("❌ ID invalide")
    
    elif choice == '3':
        schema_name = input("\n👉 Entrez le nom du schéma: ").strip()
        delete_tenant(schema_name=schema_name)
    
    elif choice == '4':
        print("\n👋 Au revoir !")
        return
    
    else:
        print("\n❌ Choix invalide")

if __name__ == '__main__':
    main()
