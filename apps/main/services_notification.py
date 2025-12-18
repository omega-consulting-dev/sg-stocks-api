"""
Service pour créer et gérer les notifications
"""
from typing import List, Optional
from django.db.models import Q
from apps.main.models_notification import Notification
from apps.accounts.models import User


class NotificationService:
    """Service pour créer des notifications"""
    
    @staticmethod
    def create_notification(
        user: User,
        notification_type: str,
        title: str,
        message: str,
        priority: str = 'medium',
        data: Optional[dict] = None,
        action_url: Optional[str] = None
    ) -> Notification:
        """Créer une notification pour un utilisateur"""
        return Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            data=data,
            action_url=action_url
        )
    
    @staticmethod
    def notify_users_with_permission(
        permission: str,
        notification_type: str,
        title: str,
        message: str,
        priority: str = 'medium',
        data: Optional[dict] = None,
        action_url: Optional[str] = None
    ) -> List[Notification]:
        """Créer des notifications pour tous les utilisateurs avec une permission spécifique"""
        users = User.objects.filter(
            Q(**{permission: True}) | Q(is_superuser=True)
        ).distinct()
        
        notifications = []
        for user in users:
            notification = NotificationService.create_notification(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                priority=priority,
                data=data,
                action_url=action_url
            )
            notifications.append(notification)
        
        return notifications
    
    @staticmethod
    def notify_stock_rupture(product, users: Optional[List[User]] = None):
        """Notifier une rupture de stock"""
        title = f"Rupture de stock: {product.name}"
        message = f"Le produit '{product.name}' (Réf: {product.reference}) est en rupture de stock."
        
        data = {
            'product_id': product.id,
            'product_name': product.name,
            'product_reference': product.reference,
            'current_stock': 0
        }
        
        if users:
            return [
                NotificationService.create_notification(
                    user=user,
                    notification_type='stock_rupture',
                    title=title,
                    message=message,
                    priority='urgent',
                    data=data,
                    action_url=f'/inventory/products/{product.id}'
                )
                for user in users
            ]
        
        return NotificationService.notify_users_with_permission(
            permission='can_manage_stock',
            notification_type='stock_rupture',
            title=title,
            message=message,
            priority='urgent',
            data=data,
            action_url=f'/inventory/products/{product.id}'
        )
    
    @staticmethod
    def notify_low_stock(product, current_stock, reorder_level, users: Optional[List[User]] = None):
        """Notifier un stock faible"""
        title = f"Stock faible: {product.name}"
        message = f"Le produit '{product.name}' a un stock faible ({current_stock} unités). Seuil: {reorder_level}."
        
        data = {
            'product_id': product.id,
            'product_name': product.name,
            'product_reference': product.reference,
            'current_stock': current_stock,
            'reorder_level': reorder_level
        }
        
        if users:
            return [
                NotificationService.create_notification(
                    user=user,
                    notification_type='stock_low',
                    title=title,
                    message=message,
                    priority='high',
                    data=data,
                    action_url=f'/inventory/products/{product.id}'
                )
                for user in users
            ]
        
        return NotificationService.notify_users_with_permission(
            permission='can_manage_stock',
            notification_type='stock_low',
            title=title,
            message=message,
            priority='high',
            data=data,
            action_url=f'/inventory/products/{product.id}'
        )
    
    @staticmethod
    def notify_debt_due(loan, users: Optional[List[User]] = None):
        """Notifier une échéance de dette"""
        entity_name = loan.customer.name if hasattr(loan, 'customer') else loan.supplier.name
        entity_type = 'client' if hasattr(loan, 'customer') else 'fournisseur'
        
        title = f"Échéance de paiement: {entity_name}"
        message = f"Échéance de paiement pour {entity_type} '{entity_name}': {loan.amount_due} FCFA le {loan.due_date.strftime('%d/%m/%Y')}."
        
        data = {
            'loan_id': loan.id,
            'entity_name': entity_name,
            'entity_type': entity_type,
            'amount_due': float(loan.amount_due),
            'due_date': loan.due_date.isoformat()
        }
        
        if users:
            return [
                NotificationService.create_notification(
                    user=user,
                    notification_type='debt_due',
                    title=title,
                    message=message,
                    priority='high',
                    data=data,
                    action_url=f'/loans/{loan.id}'
                )
                for user in users
            ]
        
        return NotificationService.notify_users_with_permission(
            permission='can_manage_loans',
            notification_type='debt_due',
            title=title,
            message=message,
            priority='high',
            data=data,
            action_url=f'/loans/{loan.id}'
        )
    
    @staticmethod
    def notify_transfer_pending(transfer, users: Optional[List[User]] = None):
        """Notifier un transfert en attente de validation"""
        title = f"Transfert en attente de validation"
        message = f"Un transfert de stock nécessite votre validation: {transfer.quantity} unités de '{transfer.product.name}'."
        
        data = {
            'transfer_id': transfer.id,
            'product_name': transfer.product.name,
            'quantity': transfer.quantity,
            'from_location': transfer.from_location.name if hasattr(transfer, 'from_location') else 'N/A',
            'to_location': transfer.to_location.name if hasattr(transfer, 'to_location') else 'N/A',
        }
        
        if users:
            return [
                NotificationService.create_notification(
                    user=user,
                    notification_type='transfer_pending',
                    title=title,
                    message=message,
                    priority='medium',
                    data=data,
                    action_url=f'/inventory/transfers/{transfer.id}'
                )
                for user in users
            ]
        
        return NotificationService.notify_users_with_permission(
            permission='can_manage_stock',
            notification_type='transfer_pending',
            title=title,
            message=message,
            priority='medium',
            data=data,
            action_url=f'/inventory/transfers/{transfer.id}'
        )
    
    @staticmethod
    def notify_payment_received(payment, users: Optional[List[User]] = None):
        """Notifier un paiement reçu"""
        entity_name = payment.customer.name if hasattr(payment, 'customer') else payment.supplier.name
        
        title = f"Paiement reçu: {entity_name}"
        message = f"Paiement de {payment.amount} FCFA reçu de {entity_name}."
        
        data = {
            'payment_id': payment.id,
            'entity_name': entity_name,
            'amount': float(payment.amount),
            'payment_date': payment.payment_date.isoformat() if hasattr(payment, 'payment_date') else None
        }
        
        if users:
            return [
                NotificationService.create_notification(
                    user=user,
                    notification_type='payment_received',
                    title=title,
                    message=message,
                    priority='low',
                    data=data,
                    action_url=f'/payments/{payment.id}'
                )
                for user in users
            ]
        
        return NotificationService.notify_users_with_permission(
            permission='can_manage_loans',
            notification_type='payment_received',
            title=title,
            message=message,
            priority='low',
            data=data,
            action_url=f'/payments/{payment.id}'
        )
    
    @staticmethod
    def notify_invoice_created(invoice, users: Optional[List[User]] = None):
        """Notifier la création d'une facture"""
        title = f"Nouvelle facture: {invoice.invoice_number}"
        message = f"Facture {invoice.invoice_number} créée pour {invoice.customer.name} - Montant: {invoice.total_amount} FCFA."
        
        data = {
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'customer_name': invoice.customer.name,
            'total_amount': float(invoice.total_amount)
        }
        
        if users:
            return [
                NotificationService.create_notification(
                    user=user,
                    notification_type='invoice_created',
                    title=title,
                    message=message,
                    priority='low',
                    data=data,
                    action_url=f'/invoices/{invoice.id}'
                )
                for user in users
            ]
        
        return NotificationService.notify_users_with_permission(
            permission='can_manage_invoices',
            notification_type='invoice_created',
            title=title,
            message=message,
            priority='low',
            data=data,
            action_url=f'/invoices/{invoice.id}'
        )
