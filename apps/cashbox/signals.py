"""
Signals pour la gestion automatique des caisses.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from apps.inventory.models import Store
from decimal import Decimal


@receiver(post_save, sender=Store)
def create_cashbox_for_store(sender, instance, created, **kwargs):
    """
    Crée automatiquement une caisse quand un nouveau point de vente est créé.
    """
    if created:
        from apps.cashbox.models import Cashbox
        
        # Vérifier si une caisse existe déjà pour ce store
        if not Cashbox.objects.filter(store=instance, is_active=True).exists():
            # Vérifier si une caisse inactive avec ce code existe
            cashbox_code = f"CAISSE-{instance.code}"
            existing_cashbox = Cashbox.objects.filter(code=cashbox_code, is_active=False).first()
            
            if existing_cashbox:
                # Réactiver la caisse existante
                existing_cashbox.name = f"Caisse {instance.name}"
                existing_cashbox.store = instance
                existing_cashbox.is_active = True
                existing_cashbox.save()
            else:
                # Créer une nouvelle caisse
                Cashbox.objects.create(
                    name=f"Caisse {instance.name}",
                    code=cashbox_code,
                    store=instance,
                    current_balance=0,
                    is_active=True
                )


# ========== SIGNAUX POUR METTRE À JOUR LA CAISSE ==========

@receiver(post_save, sender='sales.Sale')
def update_cashbox_on_sale_payment(sender, instance, created, **kwargs):
    """
    Met à jour le solde de la caisse quand une vente est payée.
    """
    from apps.cashbox.models import Cashbox
    
    # Vérifier si le paid_amount a changé
    if not created and hasattr(instance, '_old_paid_amount'):
        old_paid = instance._old_paid_amount or Decimal('0')
        new_paid = instance.paid_amount or Decimal('0')
        difference = new_paid - old_paid
        
        if difference != 0 and instance.store:
            cashbox = Cashbox.objects.filter(
                store=instance.store,
                is_active=True
            ).first()
            
            if cashbox:
                with transaction.atomic():
                    cashbox.current_balance += difference
                    cashbox.save(update_fields=['current_balance'])


@receiver(pre_save, sender='sales.Sale')
def track_sale_payment_change(sender, instance, **kwargs):
    """Suivre les changements de paiement des ventes."""
    if instance.pk:
        try:
            from apps.sales.models import Sale
            old_sale = Sale.objects.get(pk=instance.pk)
            instance._old_paid_amount = old_sale.paid_amount
        except:
            instance._old_paid_amount = Decimal('0')
    else:
        instance._old_paid_amount = Decimal('0')


@receiver(post_save, sender='invoicing.InvoicePayment')
def update_cashbox_on_invoice_payment(sender, instance, created, **kwargs):
    """
    Met à jour le solde de la caisse quand un paiement de facture en espèces est effectué.
    """
    from apps.cashbox.models import Cashbox
    
    if created and instance.payment_method == 'cash' and instance.invoice.store:
        cashbox = Cashbox.objects.filter(
            store=instance.invoice.store,
            is_active=True
        ).first()
        
        if cashbox:
            with transaction.atomic():
                cashbox.current_balance += instance.amount
                cashbox.save(update_fields=['current_balance'])


# Signal supprimé: update_cashbox_on_supplier_payment
# La mise à jour du solde de la caisse est déjà gérée dans suppliers/serializers.py ligne 288
# pour éviter le double débit (voir SupplierPaymentSerializer.create())


@receiver(post_save, sender='cashbox.CashMovement')
def update_cashbox_on_cash_movement(sender, instance, created, **kwargs):
    """
    Met à jour le solde de la caisse lors des mouvements de caisse.
    """
    from apps.cashbox.models import Cashbox
    
    if created and instance.cashbox_session:
        with transaction.atomic():
            cashbox = Cashbox.objects.select_for_update().get(pk=instance.cashbox_session.cashbox.pk)
            
            if instance.movement_type == 'in':
                # Entrée d'argent
                cashbox.current_balance += instance.amount
            elif instance.movement_type == 'out':
                # Sortie d'argent
                cashbox.current_balance -= instance.amount
            
            cashbox.save(update_fields=['current_balance'])


# Signal supprimé: update_cashbox_on_loan_payment
# La mise à jour du solde de la caisse est déjà gérée dans loans/views.py lors de la création du paiement
# pour éviter le double débit (voir ligne 229 de loans/views.py)

