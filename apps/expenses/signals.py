"""
Signals for Expense app - Manage cashbox balance when expenses are paid from cash.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from apps.expenses.models import Expense
from apps.cashbox.models import Cashbox


@receiver(pre_save, sender=Expense)
def track_expense_payment_change(sender, instance, **kwargs):
    """Track if expense is being marked as paid to update cashbox."""
    if instance.pk:
        # Récupérer l'ancienne version
        try:
            instance._old_instance = Expense.objects.get(pk=instance.pk)
        except Expense.DoesNotExist:
            instance._old_instance = None
    else:
        instance._old_instance = None


@receiver(post_save, sender=Expense)
def update_cashbox_on_expense_payment(sender, instance, created, **kwargs):
    """
    Diminue automatiquement le solde de la caisse quand une dépense est payée en espèces.
    
    Conditions:
    - status = 'paid'
    - payment_method = 'cash'
    - Un store est assigné
    """
    # Vérifier si la dépense vient d'être marquée comme payée en espèces
    old_instance = getattr(instance, '_old_instance', None)
    
    # Déterminer si on doit déduire de la caisse
    should_deduct = False
    
    if created and instance.status == 'paid' and instance.payment_method == 'cash':
        # Nouvelle dépense déjà marquée comme payée en espèces
        should_deduct = True
    elif old_instance:
        # Dépense existante - vérifier si elle vient d'être marquée comme payée
        status_changed = old_instance.status != instance.status
        payment_method_changed = old_instance.payment_method != instance.payment_method
        
        if status_changed and instance.status == 'paid' and instance.payment_method == 'cash':
            should_deduct = True
        elif payment_method_changed and instance.status == 'paid' and instance.payment_method == 'cash':
            should_deduct = True
    
    if should_deduct and instance.store:
        # Trouver la caisse active du store
        try:
            cashbox = Cashbox.objects.filter(
                store=instance.store,
                is_active=True
            ).first()
            
            if cashbox:
                with transaction.atomic():
                    # Déduire le montant de la caisse
                    cashbox.current_balance -= instance.amount
                    cashbox.save(update_fields=['current_balance'])
        except Exception:
            pass


@receiver(post_save, sender=Expense)
def restore_cashbox_on_expense_rejection(sender, instance, created, **kwargs):
    """
    Restaure le solde de la caisse si une dépense payée en espèces est rejetée.
    """
    old_instance = getattr(instance, '_old_instance', None)
    
    if old_instance:
        if old_instance.status == 'paid' and old_instance.payment_method == 'cash':
            if instance.status == 'rejected':
                if instance.store:
                    # La dépense est passée de 'paid' à 'rejected'
                    # On doit restaurer le montant dans la caisse
                    try:
                        cashbox = Cashbox.objects.filter(
                            store=instance.store,
                            is_active=True
                        ).first()
                        
                        if cashbox:
                            with transaction.atomic():
                                cashbox.current_balance += instance.amount
                                cashbox.save(update_fields=['current_balance'])
                    except Exception:
                        pass

