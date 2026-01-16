#!/usr/bin/env python
"""
Supprimer la table FieldConfiguration du schéma public
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection

print("\n" + "=" * 70)
print("Suppression de core_fieldconfiguration du schéma public")
print("=" * 70)

# Basculer au schéma public
connection.set_schema_to_public()

# Vérifier si la table existe
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'core_fieldconfiguration'
        );
    """)
    exists = cursor.fetchone()[0]
    
    if exists:
        print("\n✓ Table core_fieldconfiguration trouvée dans le schéma public")
        print("  Suppression en cours...")
        cursor.execute("DROP TABLE IF EXISTS public.core_fieldconfiguration CASCADE;")
        print("  ✓ Table supprimée du schéma public")
    else:
        print("\n✓ Table core_fieldconfiguration n'existe pas dans le schéma public")

print("\n" + "=" * 70)
print("[OK] Terminé! La table n'existe plus dans public")
print("=" * 70)
