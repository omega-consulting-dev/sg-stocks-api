"""
Middleware for tracking user sessions and activities.
"""

from django_tenants.utils import get_tenant, get_public_schema_name
from django.utils import timezone
from apps.accounts.models import UserSession, UserActivity

class TenantMiddlewareMixin:
    """
    Mixin pour vérifier si la requête est destinée à un schéma de tenant (non-public).
    """
    @staticmethod
    def is_tenant_schema(request):
        """Retourne True si le schéma actif n'est pas le schéma public."""
        try:
            return get_tenant().schema_name != get_public_schema_name()
        except Exception:
            return False

class UserSessionMiddleware(TenantMiddlewareMixin):
    """
    Middleware pour gérer les sessions utilisateurs. 
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if not self.is_tenant_schema(request):
            return self.get_response(request)

        if request.user.is_authenticated:
            # Récupérer ou créer la session
            session_key = request.session.session_key
            
            if session_key and not hasattr(request, '_user_session_processed'):
                # Marquer comme traité pour éviter les doublons
                request._user_session_processed = True
                
                # Créer ou mettre à jour la session
                user_session, created = UserSession.objects.get_or_create(
                    session_key=session_key,
                    defaults={
                        'user': request.user,
                        'ip_address': self.get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                        'is_active': True,
                    }
                )
                
                if not created and not user_session.is_active:
                    # Réactiver la session si elle était inactive
                    user_session.is_active = True
                    user_session.save()
        
        response = self.get_response(request)
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Récupérer l'adresse IP du client."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserActivityMiddleware(TenantMiddlewareMixin):
    """
    Middleware pour enregistrer les activités des utilisateurs.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if not self.is_tenant_schema(request):
            return self.get_response(request)

        response = self.get_response(request)
        
        # Enregistrer l'activité après la réponse
        if request.user.is_authenticated and self.should_log_activity(request):
            self.log_activity(request, response)
        
        return response
    
    def should_log_activity(self, request):
        """Déterminer si l'activité doit être enregistrée."""
        # Ne pas logger les requêtes GET (sauf certaines)
        if request.method == 'GET' and not request.path.endswith('/export/'):
            return False
        
        # Ne pas logger les endpoints d'authentification
        if '/api/v1/auth/' in request.path:
            return False
        
        # Ne pas logger les requêtes statiques
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return False
        
        return True
    
    def log_activity(self, request, response):
        """Enregistrer l'activité de l'utilisateur."""
        try:
            # Mapper les méthodes HTTP aux actions
            action_map = {
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'update',
                'DELETE': 'delete',
            }
            
            action = action_map.get(request.method, 'view')
            
            # Extraire le module depuis l'URL
            path_parts = request.path.strip('/').split('/')
            module = path_parts[2] if len(path_parts) > 2 else 'unknown'
            
            # Créer la description
            description = f"{request.method} {request.path}"
            
            # Enregistrer l'activité
            UserActivity.objects.create(
                user=request.user,
                action=action,
                module=module,
                description=description,
                ip_address=UserSessionMiddleware.get_client_ip(request)
            )
        except Exception as e:
            # Ne pas bloquer la requête en cas d'erreur
            print(f"Error logging activity: {e}")


class LoginLogoutMiddleware(TenantMiddlewareMixin):
    """
    Middleware pour enregistrer les connexions et déconnexions.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):

        if not self.is_tenant_schema(request):
            return self.get_response(request)
        
        response = self.get_response(request)
        
        # Détecter les connexions
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.path.endswith('/login/') and request.method == 'POST':
                if response.status_code == 200:
                    self.log_login(request)
        
        return response
    
    def log_login(self, request):
        """Enregistrer une connexion."""
        try:
            UserActivity.objects.create(
                user=request.user,
                action='login',
                module='auth',
                description=f"Connexion réussie depuis {UserSessionMiddleware.get_client_ip(request)}",
                ip_address=UserSessionMiddleware.get_client_ip(request)
            )
        except Exception as e:
            print(f"Error logging login: {e}")
