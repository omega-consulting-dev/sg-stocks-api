# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stocktransfer',
            name='reference',
            field=models.CharField(blank=True, max_length=100, verbose_name='Référence'),
        ),
    ]
