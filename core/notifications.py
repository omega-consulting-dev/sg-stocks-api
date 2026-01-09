"""
Script utilitaire pour créer des notifications
"""
from django.contrib.auth import get_user_model
from apps.accounts.models import Notification

User = get_user_model()


def create_notification(
    user,
    notification_type,
    title,
    message,
    priority='medium',
    data=None,
    action_url=None
):
    """
    Créer une notification pour un utilisateur et l'envoyer via WebSocket
    
    Args:
        user: Instance User
        notification_type: Type de notification (stock_rupture, debt_due, etc.)
        title: Titre de la notification
        message: Message de la notification
        priority: Priorité (low, medium, high, urgent)
        data: Données JSON additionnelles
        action_url: URL de redirection
    
    Returns:
        Notification instance
    """
    notification = Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        message=message,
        priority=priority,
        data=data or {},
        action_url=action_url
    )
    
    # Envoyer la notification via WebSocket
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from django.db import connection
        
        channel_layer = get_channel_layer()
        if channel_layer:
            # Get current tenant schema
            tenant_schema = connection.schema_name if hasattr(connection, 'schema_name') else 'public'
            
            notification_data = {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'priority': notification.priority,
                'category': notification.type,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat(),
            }
            
            # Send to user's notification group (with tenant schema)
            group_name = f"notifications_{tenant_schema}_{user.id}"
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'notification_new',
                    'notification': notification_data
                }
            )
    except Exception as e:
        print(f"Erreur WebSocket pour notification: {e}")
    
    return notification


def notify_stock_rupture(user, product_name, product_id):
    """Notifier une rupture de stock"""
    return create_notification(
        user=user,
        notification_type='stock_rupture',
        title=f'Rupture de stock: {product_name}',
        message=f'Le produit "{product_name}" est en rupture de stock. Veuillez réapprovisionner.',
        priority='urgent',
        data={'product_id': product_id, 'product_name': product_name},
        action_url=f'/inventory/products/{product_id}'
    )


def notify_stock_low(user, product_name, product_id, current_quantity, reorder_level):
    """Notifier un stock faible"""
    return create_notification(
        user=user,
        notification_type='stock_low',
        title=f'Stock faible: {product_name}',
        message=f'Le produit "{product_name}" a un stock faible ({current_quantity} unités, seuil: {reorder_level}).',
        priority='high',
        data={
            'product_id': product_id,
            'product_name': product_name,
            'current_quantity': float(current_quantity),
            'reorder_level': float(reorder_level)
        },
        action_url=f'/inventory/products/{product_id}'
    )


def notify_debt_due(user, client_name, client_id, amount, due_date):
    """Notifier une échéance de dette"""
    return create_notification(
        user=user,
        notification_type='debt_due',
        title=f'Échéance de paiement: {client_name}',
        message=f'Le client "{client_name}" a un paiement de {amount} FCFA qui arrive à échéance le {due_date}.',
        priority='high',
        data={
            'client_id': client_id,
            'client_name': client_name,
            'amount': amount,
            'due_date': due_date
        },
        action_url=f'/customers/{client_id}/debts'
    )


def notify_transfer_pending(user, transfer_id, from_warehouse, to_warehouse):
    """Notifier un transfert en attente de validation"""
    return create_notification(
        user=user,
        notification_type='transfer_pending',
        title='Transfert en attente de validation',
        message=f'Un transfert de stock de "{from_warehouse}" vers "{to_warehouse}" nécessite votre validation.',
        priority='medium',
        data={
            'transfer_id': transfer_id,
            'from_warehouse': from_warehouse,
            'to_warehouse': to_warehouse
        },
        action_url=f'/inventory/transfers/{transfer_id}'
    )


def notify_transfer_validated(user, transfer_id, from_warehouse, to_warehouse):
    """Notifier un transfert validé"""
    return create_notification(
        user=user,
        notification_type='transfer_validated',
        title='Transfert validé',
        message=f'Le transfert de "{from_warehouse}" vers "{to_warehouse}" a été validé avec succès.',
        priority='low',
        data={
            'transfer_id': transfer_id,
            'from_warehouse': from_warehouse,
            'to_warehouse': to_warehouse
        },
        action_url=f'/inventory/transfers/{transfer_id}'
    )


def notify_transfer_received(user, transfer_id, transfer_number, from_warehouse, to_warehouse, total_items):
    """Notifier la réception d'un transfert de stock"""
    return create_notification(
        user=user,
        notification_type='transfer_received',
        title='📦 Transfert de stock reçu',
        message=f'Transfert {transfer_number} reçu : {total_items} article(s) transféré(s) de "{from_warehouse}" vers "{to_warehouse}".',
        priority='medium',
        data={
            'transfer_id': transfer_id,
            'transfer_number': transfer_number,
            'from_warehouse': from_warehouse,
            'to_warehouse': to_warehouse,
            'total_items': total_items
        },
        action_url=f'/inventory/transfers/{transfer_id}'
    )


def notify_payment_received(user, client_name, client_id, amount):
    """Notifier un paiement reçu"""
    return create_notification(
        user=user,
        notification_type='payment_received',
        title=f'Paiement reçu de {client_name}',
        message=f'Un paiement de {amount} FCFA a été reçu de "{client_name}".',
        priority='low',
        data={
            'client_id': client_id,
            'client_name': client_name,
            'amount': amount
        },
        action_url=f'/customers/{client_id}'
    )


def notify_payment_due(user, supplier_name, supplier_id, amount, days_overdue):
    """Notifier un paiement en retard"""
    return create_notification(
        user=user,
        notification_type='payment_due',
        title=f'Paiement en retard: {supplier_name}',
        message=f'Le paiement de {amount} FCFA au fournisseur "{supplier_name}" est en retard de {days_overdue} jours.',
        priority='urgent',
        data={
            'supplier_id': supplier_id,
            'supplier_name': supplier_name,
            'amount': amount,
            'days_overdue': days_overdue
        },
        action_url=f'/suppliers/{supplier_id}/debts'
    )


def notify_invoice_created(user, invoice_number, client_name, amount):
    """Notifier une facture créée"""
    return create_notification(
        user=user,
        notification_type='invoice_created',
        title=f'Nouvelle facture: {invoice_number}',
        message=f'La facture {invoice_number} d\'un montant de {amount} FCFA a été créée pour "{client_name}".',
        priority='low',
        data={
            'invoice_number': invoice_number,
            'client_name': client_name,
            'amount': amount
        },
        action_url=f'/invoicing/{invoice_number}'
    )


def notify_invoice_paid(user, invoice_number, client_name, amount):
    """Notifier une facture payée"""
    return create_notification(
        user=user,
        notification_type='invoice_paid',
        title=f'Facture payée: {invoice_number}',
        message=f'La facture {invoice_number} de {amount} FCFA a été payée par "{client_name}".',
        priority='low',
        data={
            'invoice_number': invoice_number,
            'client_name': client_name,
            'amount': amount
        },
        action_url=f'/invoicing/{invoice_number}'
    )


# Fonction helper pour notifier plusieurs utilisateurs
def notify_users(users, notification_func, *args, **kwargs):
    """
    Créer une notification pour plusieurs utilisateurs
    
    Args:
        users: Liste d'utilisateurs ou QuerySet
        notification_func: Fonction de notification à appeler
        *args, **kwargs: Arguments à passer à la fonction
    
    Returns:
        Liste des notifications créées
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    from django.db import connection
    
    notifications = []
    channel_layer = get_channel_layer()
    
    # Get current tenant schema
    tenant_schema = connection.schema_name if hasattr(connection, 'schema_name') else 'public'
    
    for user in users:
        try:
            notification = notification_func(user, *args, **kwargs)
            notifications.append(notification)
            
            # Broadcast to WebSocket if notification was created
            if notification and channel_layer:
                notification_data = {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'category': notification.type,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at.isoformat(),
                }
                
                # Send to user's notification group (with tenant schema)
                group_name = f"notifications_{tenant_schema}_{user.id}"
                
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'notification_new',
                        'notification': notification_data
                    }
                )
                
        except Exception as e:
            print(f"Erreur notification pour {user}: {e}")
    
    return notifications
