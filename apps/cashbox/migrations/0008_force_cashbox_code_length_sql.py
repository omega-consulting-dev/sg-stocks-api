# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cashbox', '0007_alter_cashbox_code_length'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward: augmenter à 50 caractères
            sql="""
                ALTER TABLE cashbox_cashbox ALTER COLUMN code TYPE VARCHAR(50);
            """,
            # Reverse: revenir à 20 caractères
            reverse_sql="""
                ALTER TABLE cashbox_cashbox ALTER COLUMN code TYPE VARCHAR(20);
            """,
        ),
    ]
