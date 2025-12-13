"""
Signals pour la gestion automatique des paiements fournisseurs.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from apps.suppliers.models import SupplierPayment


@receiver(post_save, sender=SupplierPayment)
def update_purchase_order_paid_amount(sender, instance, created, **kwargs):
    """
    Met à jour automatiquement le paid_amount du PurchaseOrder quand un paiement est créé.
    """
    if not instance.purchase_order:
        return
    
    with transaction.atomic():
        # Recalculer le total payé pour ce bon de commande
        purchase_order = instance.purchase_order
        total_paid = sum(
            payment.amount 
            for payment in purchase_order.payments.all()
        )
        
        purchase_order.paid_amount = total_paid
        purchase_order.save(update_fields=['paid_amount'])


@receiver(post_delete, sender=SupplierPayment)
def update_purchase_order_on_payment_delete(sender, instance, **kwargs):
    """
    Met à jour le paid_amount quand un paiement est supprimé.
    """
    if not instance.purchase_order:
        return
    
    with transaction.atomic():
        purchase_order = instance.purchase_order
        total_paid = sum(
            payment.amount 
            for payment in purchase_order.payments.all()
        )
        
        purchase_order.paid_amount = total_paid
        purchase_order.save(update_fields=['paid_amount'])
