from django.contrib.auth.backends import ModelBackend
from django_tenants.utils import get_tenant, get_public_schema_name
from django.db import connection

class TenantAuthBackend(ModelBackend):
    """
    Backend d'authentification qui gère les utilisateurs des deux schémas (Tenant et Public).
    """

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):

        login_id = email or username 
        
        if not login_id or not password:
            return None

        # Gérer le cas où get_tenant retourne None
        tenant = get_tenant(request=request) if request else None
        schema_name = tenant.schema_name if tenant else connection.schema_name
        
        if schema_name == get_public_schema_name():
            # En schéma public, on utilise le modèle configuré par AUTH_USER_MODEL
            from django.contrib.auth import get_user_model
            PublicUser = get_user_model()
            try:
                user = PublicUser.objects.get(email=login_id)
                # Uniquement les comptes staff peuvent se loguer via l'admin
                if user.check_password(password) and user.is_staff:
                    return user
            except PublicUser.DoesNotExist:
                pass

        else:
            from apps.accounts.models import User as TenantUser
            try:
                user = TenantUser.objects.get(email=login_id)
                if user.check_password(password):
                    return user
            except TenantUser.DoesNotExist:
                pass

        return None