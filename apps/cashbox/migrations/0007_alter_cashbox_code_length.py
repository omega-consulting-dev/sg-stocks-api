# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cashbox', '0006_alter_cashbox_code_unique_constraint'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashbox',
            name='code',
            field=models.CharField(max_length=50, verbose_name='Code'),
        ),
    ]
