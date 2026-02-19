# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicecategory',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Désignation'),
        ),
        migrations.AlterField(
            model_name='service',
            name='reference',
            field=models.CharField(max_length=50, verbose_name='Référence'),
        ),
        migrations.AddConstraint(
            model_name='servicecategory',
            constraint=models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(is_active=True),
                name='unique_active_service_category_name'
            ),
        ),
        migrations.AddConstraint(
            model_name='service',
            constraint=models.UniqueConstraint(
                fields=['reference'],
                condition=models.Q(is_active=True),
                name='unique_active_service_reference'
            ),
        ),
    ]
