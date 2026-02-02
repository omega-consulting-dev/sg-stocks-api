# Generated migration to ensure DEFAULT constraint

from django.db import migrations


def set_default_constraint(apps, schema_editor):
    """Ensure DEFAULT FALSE is set at database level for can_manage_mobile_money"""
    # Cette migration garantit que la contrainte DEFAULT est présente
    # Elle sera appliquée automatiquement pour tous les nouveaux tenants
    with schema_editor.connection.cursor() as cursor:
        # Vérifier et ajouter DEFAULT si nécessaire
        cursor.execute("""
            DO $$
            BEGIN
                -- Mettre à jour toutes les valeurs NULL existantes
                UPDATE accounts_role 
                SET can_manage_mobile_money = FALSE 
                WHERE can_manage_mobile_money IS NULL;
                
                -- Ajouter la contrainte DEFAULT si elle n'existe pas déjà
                ALTER TABLE accounts_role 
                ALTER COLUMN can_manage_mobile_money SET DEFAULT FALSE;
            EXCEPTION
                WHEN OTHERS THEN
                    -- Ignorer les erreurs si la contrainte existe déjà
                    NULL;
            END $$;
        """)


def reverse_default_constraint(apps, schema_editor):
    """Remove DEFAULT constraint if migration is reversed"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE accounts_role 
            ALTER COLUMN can_manage_mobile_money DROP DEFAULT;
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_can_manage_mobile_money'),
    ]

    operations = [
        migrations.RunPython(set_default_constraint, reverse_default_constraint),
    ]
