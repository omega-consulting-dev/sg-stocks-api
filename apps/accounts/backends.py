from django.contrib.auth.backends import ModelBackend
from django_tenants.utils import get_tenant, get_public_schema_name

class TenantAuthBackend(ModelBackend):
    """
    Backend d'authentification qui gère les utilisateurs des deux schémas (Tenant et Public).
    """

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):

        login_id = email or username 
        
        if not login_id or not password:
            return None

        if get_tenant(request=request).schema_name == get_public_schema_name():
            from apps.main.models import User as MainUser
            try:
                user = MainUser.objects.get(email=login_id)
                if user.check_password(password) and user.is_staff:
                    return user
            except MainUser.DoesNotExist:
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