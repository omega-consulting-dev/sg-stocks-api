from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.invoicing.models import InvoicePayment


@receiver(post_save, sender=InvoicePayment)
def update_invoice_paid_amount_on_payment_save(sender, instance, created, **kwargs):
    """
    Met à jour le montant payé de la facture quand un paiement est créé ou modifié.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if kwargs.get('raw', False):
        return
    
    # Récupérer tous les paiements de cette facture
    invoice = instance.invoice
    total_paid = sum(payment.amount for payment in invoice.payments.all())
    
    logger.info(f"Signal: Paiement {'créé' if created else 'modifié'} pour facture {invoice.invoice_number}")
    logger.info(f"Signal: Montant du paiement: {instance.amount}")
    logger.info(f"Signal: Total payé calculé: {total_paid}")
    logger.info(f"Signal: Montant payé actuel dans la facture: {invoice.paid_amount}")
    
    # Mettre à jour le montant payé
    if invoice.paid_amount != total_paid:
        invoice.paid_amount = total_paid
        
        # Mettre à jour le statut si entièrement payé
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = 'paid'
        elif invoice.paid_amount > 0:
            invoice.status = 'sent'
        
        logger.info(f"Signal: Mise à jour - paid_amount: {invoice.paid_amount}, status: {invoice.status}")
        invoice.save(update_fields=['paid_amount', 'status'])
        logger.info(f"Signal: Facture {invoice.invoice_number} mise à jour avec succès")
    else:
        logger.info(f"Signal: Pas de mise à jour nécessaire (montants identiques)")


@receiver(post_delete, sender=InvoicePayment)
def update_invoice_paid_amount_on_payment_delete(sender, instance, **kwargs):
    """
    Met à jour le montant payé de la facture quand un paiement est supprimé.
    """
    # Récupérer tous les paiements restants de cette facture
    invoice = instance.invoice
    total_paid = sum(payment.amount for payment in invoice.payments.all())
    
    # Mettre à jour le montant payé
    if invoice.paid_amount != total_paid:
        invoice.paid_amount = total_paid
        
        # Mettre à jour le statut
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = 'paid'
        elif invoice.paid_amount > 0:
            invoice.status = 'sent'
        else:
            invoice.status = 'draft'
            
        invoice.save(update_fields=['paid_amount', 'status'])
