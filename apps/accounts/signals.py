"""
Signals for accounts app.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from apps.accounts.models import User, UserActivity, UserSession


@receiver(pre_save, sender=User)
def generate_codes(sender, instance, **kwargs):
    """
    Générer automatiquement les codes si non fournis.
    """
    # Générer le code client si c'est un client et qu'il n'a pas de code
    if instance.is_customer and not instance.customer_code:
        # Compter les clients existants
        count = User.objects.filter(is_customer=True).count() + 1
        instance.customer_code = f"CLI{count:05d}"
    
    # Générer le code fournisseur si c'est un fournisseur et qu'il n'a pas de code
    if instance.is_supplier and not instance.supplier_code:
        # Compter les fournisseurs existants
        count = User.objects.filter(is_supplier=True).count() + 1
        instance.supplier_code = f"FOU{count:05d}"
    
    # Générer le matricule employé si c'est un collaborateur et qu'il n'a pas de matricule
    if instance.is_collaborator and not instance.employee_id:
        # Compter les collaborateurs existants
        count = User.objects.filter(is_collaborator=True).count() + 1
        instance.employee_id = f"EMP{count:05d}"


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Actions après la sauvegarde d'un utilisateur.
    """
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
        
        # If the new user is a supplier, ensure a Supplier record exists
        try:
            if getattr(instance, 'is_supplier', False):
                # import here to avoid circular import at module load
                from apps.suppliers.models import Supplier

                Supplier.objects.get_or_create(
                    user=instance,
                    defaults={
                        'supplier_code': getattr(instance, 'supplier_code', instance.username),
                        'name': getattr(instance, 'supplier_company_name', instance.get_display_name()),
                        'email': instance.email or ''
                    }
                )
        except Exception as e:
            print(f"Error creating Supplier for user: {e}")
        
        # If the new user is a customer, ensure a Customer record exists
        try:
            if getattr(instance, 'is_customer', False):
                # import here to avoid circular import at module load
                from apps.customers.models import Customer

                Customer.objects.get_or_create(
                    user=instance,
                    defaults={
                        'customer_code': getattr(instance, 'customer_code', instance.username),
                        'name': getattr(instance, 'customer_company_name', instance.get_display_name()),
                        'email': instance.email or ''
                    }
                )
        except Exception as e:
            print(f"Error creating Customer for user: {e}")


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