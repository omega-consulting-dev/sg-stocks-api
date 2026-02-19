# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0004_alter_expense_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expensecategory',
            name='code',
            field=models.CharField(max_length=20, verbose_name='Code'),
        ),
        migrations.AddConstraint(
            model_name='expensecategory',
            constraint=models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(is_active=True),
                name='unique_active_expense_category_code'
            ),
        ),
    ]
