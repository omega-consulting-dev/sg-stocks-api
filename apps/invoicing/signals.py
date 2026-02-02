from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.invoicing.models import InvoicePayment, Invoice, create_stock_movements_from_invoice


@receiver(post_save, sender=InvoicePayment)
def update_invoice_paid_amount_on_payment_save(sender, instance, created, **kwargs):
    """
    Met à jour le montant payé de la facture quand un paiement est créé ou modifié.
    Créé également un mouvement de caisse ou bancaire selon le mode de paiement.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if kwargs.get('raw', False):
        return
    
    # Récupérer tous les paiements réussis de cette facture
    invoice = instance.invoice
    total_paid = sum(payment.amount for payment in invoice.payments.filter(status='success'))
    
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
    
    # Créer le mouvement de caisse/banque si c'est un nouveau paiement réussi
    if created and instance.status == 'success':
        from apps.cashbox.models import CashMovement, Cashbox, CashboxSession
        from django.utils import timezone
        
        payment_method = instance.payment_method
        store = invoice.store
        
        # Pour les paiements en espèces, créer un mouvement de caisse
        if payment_method == 'cash':
            # Récupérer ou créer la caisse du store
            cashbox, _ = Cashbox.objects.get_or_create(
                store=store,
                is_active=True,
                defaults={
                    'name': f'Caisse {store.name}',
                    'code': f'CASH-{store.code}',
                    'created_by': instance.created_by
                }
            )
            
            # Récupérer ou créer une session ouverte
            cashbox_session, _ = CashboxSession.objects.get_or_create(
                cashbox=cashbox,
                status='open',
                defaults={
                    'cashier': instance.created_by,
                    'opening_date': timezone.now(),
                    'opening_balance': 0,
                    'created_by': instance.created_by
                }
            )
            
            # Générer le numéro de mouvement
            last_movement = CashMovement.objects.order_by('-id').first()
            movement_count = 1
            if last_movement and last_movement.movement_number:
                try:
                    import re
                    match = re.search(r'\\d+', last_movement.movement_number)
                    if match:
                        movement_count = int(match.group()) + 1
                except (ValueError, AttributeError):
                    movement_count = CashMovement.objects.count() + 1
            
            # Créer le mouvement de caisse (entrée d'argent)
            CashMovement.objects.create(
                movement_number=f'INV-PAY-{movement_count:05d}',
                cashbox_session=cashbox_session,
                movement_type='in',
                category='customer_payment',
                amount=instance.amount,
                payment_method='cash',
                reference=instance.payment_number,
                description=f'Paiement facture {invoice.invoice_number} - Client: {invoice.customer.name}',
                created_by=instance.created_by
            )
            
            # Mettre à jour le solde de la caisse
            cashbox.current_balance += instance.amount
            cashbox.save()
            
            logger.info(f"Signal: Mouvement de caisse créé pour paiement {instance.payment_number}")
        
        # Pour les paiements par carte, virement ou mobile money, l'argent va directement en banque/mobile money
        # On ne crée PAS de CashMovement, le InvoicePayment suffit
        # Le calcul du solde bancaire/mobile money prendra en compte
        # les InvoicePayment avec payment_method='card', 'bank_transfer' ou 'mobile_money'
        elif payment_method in ['card', 'transfer', 'bank_transfer', 'mobile_money']:
            destination = 'banque' if payment_method in ['card', 'transfer', 'bank_transfer'] else 'Mobile Money (MTN/Orange)'
            logger.info(f"Signal: Paiement par {payment_method} - argent ajouté directement en {destination}")


@receiver(post_delete, sender=InvoicePayment)
def update_invoice_paid_amount_on_payment_delete(sender, instance, **kwargs):
    """
    Met à jour le montant payé de la facture quand un paiement est supprimé.
    """
    # Récupérer tous les paiements réussis restants de cette facture
    invoice = instance.invoice
    total_paid = sum(payment.amount for payment in invoice.payments.filter(status='success'))
    
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


@receiver(post_save, sender=Invoice)
def create_invoice_stock_movements(sender, instance, created, **kwargs):
    """
    Créer automatiquement les mouvements de stock quand une facture est créée.
    """
    if kwargs.get('raw', False):
        return
    
    # Appeler la fonction qui crée les mouvements de stock
    if created:
        create_stock_movements_from_invoice(sender=sender, instance=instance, created=created)
