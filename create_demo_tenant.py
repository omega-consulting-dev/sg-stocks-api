#!/usr/bin/env python
"""
Script pour créer un tenant de démo permanent.
Ce tenant sera utilisé par tous les visiteurs qui veulent tester l'application.
"""
import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.tenants.models import Company, Domain
from django_tenants.utils import schema_context

def create_demo_tenant():
    """Créer le tenant de démo s'il n'existe pas"""
    print("="*80)
    print("CRÉATION DU TENANT DE DÉMO")
    print("="*80)
    print()
    
    # Vérifier si le tenant existe déjà
    demo = Company.objects.filter(schema_name='demo').first()
    
    if demo:
        print("[ATTENTION]  Le tenant 'demo' existe déjà!")
        print(f"   Nom: {demo.name}")
        print(f"   Email: {demo.email}")
        print()
        choice = input("Voulez-vous le supprimer et le recréer? (o/N): ").strip().lower()
        if choice != 'o':
            print("[ERREUR] Opération annulée")
            return False
        
        print("[SUPPRESSION]  Suppression de l'ancien tenant démo...")
        demo.delete()
        print("[OK] Ancien tenant supprimé")
        print()
    
    # Créer le nouveau tenant
    print("[NOTE] Création du tenant 'demo'...")
    demo = Company.objects.create(
        schema_name='demo',
        name='Démo SG-Stock',
        email='demo@sgstock.cm',
        phone='+237 600 000 000',
        address='Douala, Cameroun',
        plan='business',  # Plan business pour avoir toutes les fonctionnalités
        is_active=True,
        
        # Limites généreuses pour la démo
        max_users=10,
        max_stores=2,
        max_products=999999,
        max_storage_mb=5000,
        
        # Activer toutes les fonctionnalités
        feature_services=True,
        feature_multi_store=True,
        feature_loans=True,
        feature_advanced_analytics=True,
        feature_api_access=False,
        
        # Abonnement permanent (pas d'expiration)
        trial_end_date=None,
        subscription_end_date=date.today() + timedelta(days=3650),  # 10 ans
        
        monthly_price=Decimal('0.00'),  # Gratuit
        currency='XAF',
        tax_rate=Decimal('19.25')
    )
    print(f"[OK] Tenant créé: {demo.name}")
    print()
    
    # Créer les domaines
    print(" Création des domaines...")
    
    # Domaine localhost (développement)
    Domain.objects.create(
        domain='demo.localhost',
        tenant=demo,
        is_primary=False  # Secondaire (pour développement local)
    )
    print("   [OK] demo.localhost (développement)")
    
    # Domaine production (PRINCIPAL)
    Domain.objects.create(
        domain='demo.sg-stocks.com',
        tenant=demo,
        is_primary=True  # Principal (production)
    )
    print("   [OK] demo.sg-stocks.com (PRINCIPAL)")
    
    # Créer le DNS Cloudflare automatiquement
    print("\n☁️  Création du DNS Cloudflare...")
    try:
        from apps.tenants.cloudflare_service import CloudflareService
        cloudflare = CloudflareService()
        result = cloudflare.create_dns_record('demo', proxied=True)
        if result:
            print("   [OK] DNS demo.sg-stocks.com créé dans Cloudflare")
        else:
            print("   [ATTENTION] Échec de création DNS Cloudflare - créez-le manuellement")
    except Exception as e:
        print(f"   [ATTENTION] Erreur DNS Cloudflare: {e}")
    
    print()
    
    # Créer l'utilisateur admin démo
    print("👤 Création de l'utilisateur admin démo...")
    with schema_context('demo'):
        from apps.accounts.models import User, Role
        
        # Créer le rôle super admin s'il n'existe pas
        admin_role, created = Role.objects.get_or_create(
            name='super_admin',
            defaults={
                'display_name': 'Super Administrateur',
                'description': 'Accès complet à toutes les fonctionnalités',
                'access_scope': 'all',
                'can_manage_users': True,
                'can_manage_products': True,
                'can_view_products': True,
                'can_manage_categories': True,
                'can_view_categories': True,
                'can_manage_services': True,
                'can_view_services': True,
                'can_manage_inventory': True,
                'can_view_inventory': True,
                'can_manage_sales': True,
                'can_manage_customers': True,
                'can_manage_suppliers': True,
                'can_manage_cashbox': True,
                'can_manage_loans': True,
                'can_manage_expenses': True,
                'can_view_analytics': True,
                'can_export_data': True,
            }
        )
        
        # Créer l'utilisateur
        if User.objects.filter(email='demo@sgstock.cm').exists():
            admin_user = User.objects.get(email='demo@sgstock.cm')
            admin_user.set_password('demo1234')
            admin_user.save()
            print("   [OK] Utilisateur démo mis à jour")
        else:
            admin_user = User.objects.create_user(
                username='demo',
                email='demo@sgstock.cm',
                password='demo1234',
                first_name='Démo',
                last_name='Admin',
                role=admin_role,
                is_active=True,
                is_staff=False,
                is_superuser=False
            )
            print("   [OK] Utilisateur démo créé")
    
    print()
    print("="*80)
    print("✅ TENANT DE DÉMO CRÉÉ AVEC SUCCÈS!")
    print("="*80)
    print()
    print("📋 INFORMATIONS DE CONNEXION:")
    print(f"   URL Local      : http://demo.localhost:5173")
    print(f"   URL Production : https://demo.sg-stocks.com")
    print(f"   Email          : demo@sgstock.cm")
    print(f"   Password       : demo1234")
    print()
    print("📊 LIMITES DU TENANT DÉMO:")
    print(f"   • Utilisateurs max    : 10")
    print(f"   • Magasins max        : 2")
    print(f"   • Produits max        : 999,999 (illimité)")
    print(f"   • Stockage max        : 5 GB")
    print(f"   • Plan                : Business (toutes fonctionnalités)")
    print(f"   • Expiration          : {date.today() + timedelta(days=3650)} (10 ans)")
    print()
    print("⚠️  IMPORTANT:")
    print("   - Ce tenant est PARTAGÉ par tous les visiteurs de la démo")
    print("   - Les clients peuvent créer autant de produits qu'ils veulent")
    print("   - Pensez à RÉINITIALISER les données quotidiennement (cron job)")
    print("   - Utilisez ce tenant pour montrer l'application aux prospects")
    print()
    print("💡 UTILISATION:")
    print("   1. Partagez le lien: https://demo.sg-stocks.com")
    print("   2. Les clients testent avec: demo@sgstock.cm / demo1234")
    print("   3. Ils peuvent créer produits, ventes, clients, etc.")
    print("   4. Toutes les fonctionnalités sont activées")
    print()
    
    return True

if __name__ == '__main__':
    try:
        create_demo_tenant()
    except Exception as e:
        print(f"[ERREUR] ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
