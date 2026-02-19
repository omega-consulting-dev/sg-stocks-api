# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0002_alter_supplierpayment_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplier',
            name='supplier_code',
            field=models.CharField(max_length=50, verbose_name='Code fournisseur'),
        ),
        migrations.AddConstraint(
            model_name='supplier',
            constraint=models.UniqueConstraint(
                fields=['supplier_code'],
                condition=models.Q(is_active=True),
                name='unique_active_supplier_code'
            ),
        ),
    ]
