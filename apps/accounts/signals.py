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
    Générer automatiquement le matricule employé si non fourni.
    """
    # Générer le matricule employé s'il n'a pas de matricule
    if not instance.employee_id:
        # Compter les employés existants
        count = User.objects.count() + 1
        instance.employee_id = f"EMP{count:05d}"


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