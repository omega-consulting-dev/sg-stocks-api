"""
Signals for accounts app.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from apps.accounts.models import User, UserActivity, UserSession


# ============= NOTIFICATIONS AUTOMATIQUES =============

@receiver(post_save, sender='invoicing.InvoicePayment')
def notify_customer_payment(sender, instance, created, **kwargs):
    """Notifier lors d'un paiement client - uniquement le créateur"""
    if created and hasattr(instance, 'created_by') and instance.created_by:
        from core.notifications import notify_payment_received
        
        # Notifier uniquement l'utilisateur qui a créé le paiement
        notify_payment_received(
            user=instance.created_by,
            client_name=instance.invoice.customer.name,
            client_id=instance.invoice.customer.id,
            amount=float(instance.amount)
        )



@receiver(post_save, sender='suppliers.SupplierPayment')
def notify_supplier_payment(sender, instance, created, **kwargs):
    """Notifier lors d'un paiement fournisseur - uniquement le créateur"""
    if created and hasattr(instance, 'created_by') and instance.created_by:
        from core.notifications import notify_payment_received
        
        # Notifier uniquement l'utilisateur qui a créé le paiement
        notify_payment_received(
            user=instance.created_by,
            client_name=instance.supplier.name,
            client_id=instance.supplier.id,
            amount=float(instance.amount)
        )


@receiver(post_save, sender='invoicing.Invoice')
def notify_invoice_status_change(sender, instance, created, **kwargs):
    """Notifier lors de la création ou du changement de statut d'une facture - uniquement le créateur"""
    if created and hasattr(instance, 'created_by') and instance.created_by:
        from core.notifications import notify_invoice_created
        
        # Notifier uniquement l'utilisateur qui a créé la facture
        notify_invoice_created(
            user=instance.created_by,
            invoice_number=instance.invoice_number,
            client_name=instance.customer.name,
            amount=float(instance.total_amount)
        )
    
    elif instance.status == 'paid' and instance.paid_amount >= instance.total_amount:
        from core.notifications import notify_invoice_paid
        
        # Notifier l'utilisateur qui a créé la facture
        if hasattr(instance, 'created_by') and instance.created_by:
            notify_invoice_paid(
                user=instance.created_by,
                invoice_number=instance.invoice_number,
                client_name=instance.customer.name,
                amount=float(instance.total_amount)
            )


@receiver(post_save, sender='products.Product')
def notify_stock_issues(sender, instance, created, **kwargs):
    """
    Notifier lors de problèmes de stock - DÉSACTIVÉ
    
    Le modèle Product n'a pas d'attribut stock_quantity direct.
    Le stock est géré via le modèle Stock (stock par magasin) dans apps.inventory.
    
    [OK] Le signal de notification de stock est maintenant dans apps/inventory/signals.py
       et se déclenche sur le modèle Stock lors des modifications de stock.
    """
    pass


# ============= USER MANAGEMENT SIGNALS =============


@receiver(pre_save, sender=User)
def generate_codes(sender, instance, **kwargs):
    """
    Générer automatiquement le matricule employé si non fourni.
    """
    # Générer le matricule employé uniquement pour les nouveaux utilisateurs
    if not instance.pk and not instance.employee_id:
        # Trouver le prochain numéro disponible
        from django.db.models import Max
        import re
        
        # Récupérer le plus grand employee_id existant
        max_employee = User.objects.filter(
            employee_id__startswith='EMP'
        ).aggregate(Max('employee_id'))['employee_id__max']
        
        if max_employee:
            # Extraire le numéro du matricule (ex: EMP00004 -> 4)
            match = re.search(r'EMP(\d+)', max_employee)
            if match:
                next_num = int(match.group(1)) + 1
            else:
                next_num = 1
        else:
            next_num = 1
        
        instance.employee_id = f"EMP{next_num:05d}"


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Actions après la sauvegarde d'un utilisateur.
    """
    # Assigner automatiquement le rôle super_admin aux superusers
    if instance.is_superuser and not instance.role:
        try:
            from apps.accounts.models import Role
            super_admin_role, _ = Role.objects.get_or_create(
                name='super_admin',
                defaults={
                    'display_name': 'Super Administrateur',
                    'description': 'Accès complet à toutes les fonctionnalités',
                    'can_manage_users': True,
                    'can_manage_products': True,
                    'can_view_products': True,
                    'can_manage_categories': True,
                    'can_view_categories': True,
                    'can_manage_services': True,
                    'can_view_services': True,
                    'can_manage_inventory': True,
                    'can_view_inventory': True,
                    'can_manage_sales': True,
                    'can_manage_customers': True,
                    'can_manage_suppliers': True,
                    'can_manage_cashbox': True,
                    'can_manage_loans': True,
                    'can_manage_expenses': True,
                    'can_view_analytics': True,
                    'can_export_data': True,
                    'access_scope': 'all',
                }
            )
            instance.role = super_admin_role
            # Utiliser update pour éviter de déclencher à nouveau le signal
            User.objects.filter(pk=instance.pk).update(role=super_admin_role)
        except Exception as e:
            print(f"Error assigning super_admin role: {e}")
    
    if created:
        # Log de création d'utilisateur
        try:
            UserActivity.objects.create(
                user=instance,
                action='create',
                module='users',
                object_type='User',
                object_id=instance.id,
                description=f"Nouvel utilisateur créé: {instance.get_display_name()}",
                ip_address='127.0.0.1'  # Sera remplacé par le middleware
            )
        except Exception as e:
            print(f"Error creating user activity: {e}")



@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """
    Handler pour l'événement de connexion.
    """
    try:
        # Récupérer l'IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Enregistrer l'activité de connexion
        UserActivity.objects.create(
            user=user,
            action='login',
            module='auth',
            description=f"Connexion réussie",
            ip_address=ip
        )
        
        # Créer ou mettre à jour la session
        if hasattr(request, 'session') and request.session.session_key:
            UserSession.objects.update_or_create(
                session_key=request.session.session_key,
                defaults={
                    'user': user,
                    'ip_address': ip,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                    'is_active': True,
                }
            )
    except Exception as e:
        print(f"Error in user_logged_in_handler: {e}")


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """
    Handler pour l'événement de déconnexion.
    """
    try:
        # Récupérer l'IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Enregistrer l'activité de déconnexion
        if user:
            UserActivity.objects.create(
                user=user,
                action='logout',
                module='auth',
                description=f"Déconnexion",
                ip_address=ip
            )
            
            # Mettre à jour la session
            if hasattr(request, 'session') and request.session.session_key:
                try:
                    from django.utils import timezone
                    session = UserSession.objects.get(
                        session_key=request.session.session_key
                    )
                    session.is_active = False
                    session.logout_time = timezone.now()
                    session.save()
                except UserSession.DoesNotExist:
                    pass
    except Exception as e:
        print(f"Error in user_logged_out_handler: {e}")