# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='reference',
            field=models.CharField(max_length=50, verbose_name='Référence'),
        ),
        migrations.AlterField(
            model_name='product',
            name='barcode',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Code-barres'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.UniqueConstraint(
                fields=['reference'],
                condition=models.Q(is_active=True),
                name='unique_active_product_reference'
            ),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.UniqueConstraint(
                fields=['barcode'],
                condition=models.Q(is_active=True, barcode__isnull=False),
                name='unique_active_product_barcode'
            ),
        ),
    ]
