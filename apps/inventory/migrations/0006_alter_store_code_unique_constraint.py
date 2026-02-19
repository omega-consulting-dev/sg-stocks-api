# Generated manually on 2026-02-19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_merge_20260109_0038'),
    ]

    operations = [
        # Supprimer l'ancienne contrainte unique sur code
        migrations.AlterField(
            model_name='store',
            name='code',
            field=models.CharField(max_length=20, verbose_name='Code'),
        ),
        # Ajouter une contrainte unique conditionnelle (code unique seulement si is_active=True)
        migrations.AddConstraint(
            model_name='store',
            constraint=models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(is_active=True),
                name='unique_active_store_code'
            ),
        ),
    ]
