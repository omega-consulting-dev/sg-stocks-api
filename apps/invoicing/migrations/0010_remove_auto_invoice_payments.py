# Generated migration to remove auto-created invoice payments

from django.db import migrations


def remove_auto_invoice_payments(apps, schema_editor):
    """Remove InvoicePayment records that were auto-created with the standard message."""
    InvoicePayment = apps.get_model('invoicing', 'InvoicePayment')
    
    # Delete payments created automatically (identified by the notes field)
    InvoicePayment.objects.filter(
        notes__startswith='Paiement automatique lors de la vente'
    ).delete()


def reverse_remove_auto_invoice_payments(apps, schema_editor):
    """Reverse function - cannot restore deleted data."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0009_invoicepayment_alter_invoice_options_and_more'),
    ]

    operations = [
        migrations.RunPython(
            remove_auto_invoice_payments,
            reverse_remove_auto_invoice_payments
        ),
    ]
