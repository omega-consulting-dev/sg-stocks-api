"""
Signals for sales app to automate workflow.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Sale


@receiver(post_save, sender=Sale)
def auto_generate_invoice_on_confirmation(sender, instance, created, **kwargs):
    """
    Automatically generate an invoice when a sale is confirmed.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Signal triggered for sale {instance.id}, created={created}, status={instance.status}")
    
    if not created and instance.status == 'confirmed':
        # Check if invoice doesn't already exist
        if not hasattr(instance, 'invoice') or not instance.invoice:
            from apps.invoicing.models import Invoice
            try:
                logger.info(f"Creating invoice for sale {instance.id}")
                invoice = Invoice.generate_from_sale(instance)
                logger.info(f"Invoice {invoice.id} created successfully for sale {instance.id}")
            except Exception as e:
                # Log error but don't break the save
                logger.error(f"Failed to auto-generate invoice for sale {instance.id}: {str(e)}")
        else:
            logger.info(f"Sale {instance.id} already has invoice {instance.invoice.id}")


@receiver(post_save, sender=Sale)
def sync_payment_to_invoice(sender, instance, created, **kwargs):
    """
    Sync payment amounts between Sale and Invoice.
    """
    if not created and hasattr(instance, 'invoice') and instance.invoice:
        invoice = instance.invoice
        if invoice.paid_amount != instance.paid_amount:
            invoice.paid_amount = instance.paid_amount
            
            # Update invoice status based on payment
            if invoice.paid_amount >= invoice.total_amount:
                invoice.status = 'paid'
            elif invoice.status == 'paid' and invoice.paid_amount < invoice.total_amount:
                invoice.status = 'sent'  # Revert to sent if payment is reduced
            
            invoice.save()


# Import Invoice here to avoid circular import
from apps.invoicing.models import Invoice


@receiver(post_save, sender=Invoice)
def sync_invoice_status_to_sale(sender, instance, created, **kwargs):
    """
    Automatically mark Sale as 'completed' when Invoice is fully paid.
    This enables credit sales to automatically complete when debts are settled.
    """
    # Skip if no associated sale
    if not instance.sale:
        return
    
    sale = instance.sale
    
    # If invoice is paid and sale is confirmed, mark sale as completed
    if instance.status == 'paid' and sale.status == 'confirmed':
        try:
            sale.complete()
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Sale {sale.sale_number} automatically completed after invoice {instance.invoice_number} was paid")
        except Exception as e:
            # Log error but don't break the save
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to auto-complete sale {sale.id} after invoice payment: {str(e)}")
