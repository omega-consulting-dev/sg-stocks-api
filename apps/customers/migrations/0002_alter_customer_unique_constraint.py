# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='customer_code',
            field=models.CharField(max_length=50, verbose_name='Code client'),
        ),
        migrations.AddConstraint(
            model_name='customer',
            constraint=models.UniqueConstraint(
                fields=['customer_code'],
                condition=models.Q(is_active=True),
                name='unique_active_customer_code'
            ),
        ),
    ]
