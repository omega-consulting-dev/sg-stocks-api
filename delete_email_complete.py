"""
Script pour supprimer complètement un email du système (tenant + utilisateur public)
"""
import os
import sys
import django

# Configuration Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from apps.tenants.models import Company, Domain
from apps.main.models import User as PublicUser

email = "suzannedivine38@gmail.com"

print("=" * 80)
print(f"🗑️  Suppression complète de l'email: {email}")
print("=" * 80)

# 1. Supprimer de la table PublicUser (main_user)
print("\n1️⃣  Suppression dans public.main_user...")
public_users = PublicUser.objects.filter(email=email)
if public_users.exists():
    count = public_users.count()
    print(f"   Trouvé {count} utilisateur(s) avec cet email")
    
    confirmation = input(f"\n   ⚠️  Supprimer {count} utilisateur(s) de main_user ? (oui/non): ")
    if confirmation.lower() in ['oui', 'yes', 'o', 'y']:
        public_users.delete()
        print(f"   ✅ {count} utilisateur(s) supprimé(s) de main_user")
    else:
        print("   ❌ Suppression annulée")
else:
    print("   ✅ Aucun utilisateur trouvé dans main_user")

# 2. Supprimer les companies avec cet email
print("\n2️⃣  Suppression dans tenants_company...")
companies = Company.objects.filter(email=email)
if companies.exists():
    count = companies.count()
    print(f"   Trouvé {count} company(s) avec cet email")
    
    confirmation = input(f"\n   ⚠️  Supprimer {count} company(s) ? (oui/non): ")
    if confirmation.lower() in ['oui', 'yes', 'o', 'y']:
        for company in companies:
            print(f"   🗑️  Suppression du tenant: {company.name} ({company.schema_name})")
            
            # Supprimer le schéma PostgreSQL
            with connection.cursor() as cursor:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{company.schema_name}" CASCADE;')
            print(f"      ✅ Schéma {company.schema_name} supprimé")
            
            # Supprimer les domaines
            Domain.objects.filter(tenant=company).delete()
            print(f"      ✅ Domaines supprimés")
            
            # Supprimer la company
            company.delete()
            print(f"      ✅ Company supprimée")
    else:
        print("   ❌ Suppression annulée")
else:
    print("   ✅ Aucune company trouvée")

# 3. Vérification finale
print("\n" + "=" * 80)
print("🔍 VÉRIFICATION FINALE")
print("=" * 80)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND column_name LIKE '%email%'
        ORDER BY table_name
    """)
    tables_with_email = cursor.fetchall()
    
    found = False
    for table_name, column_name in tables_with_email:
        try:
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM public.{table_name} 
                WHERE {column_name} = %s
            """, [email])
            count = cursor.fetchone()[0]
            if count > 0:
                found = True
                print(f"   ❌ Email encore présent dans: public.{table_name}.{column_name} ({count} fois)")
        except Exception:
            pass

if not found:
    print(f"\n   ✅ L'email '{email}' a été complètement supprimé du système!")
    print("   Vous pouvez maintenant vous réinscrire avec cet email.")

print("\n" + "=" * 80)
