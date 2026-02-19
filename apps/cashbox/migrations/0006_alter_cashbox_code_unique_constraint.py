# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cashbox', '0004_alter_cashmovement_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashbox',
            name='code',
            field=models.CharField(max_length=20, verbose_name='Code'),
        ),
        migrations.AddConstraint(
            model_name='cashbox',
            constraint=models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(is_active=True),
                name='unique_active_cashbox_code'
            ),
        ),
    ]
