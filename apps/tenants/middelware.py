from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import remove_www


class TenantHeaderMiddleware(TenantMainMiddleware):
    """
    Middleware pour récupérer le domain du tenant via l'en-tête 'X-Tenant-Schema' ou hostname.
    """
    @staticmethod
    def hostname_from_request(request):
        # Récupère le hostname depuis la requête
        host = remove_www(request.get_host().split(':')[0].lower())
        
        # Si un header X-Tenant ou X-Tenant-Schema est fourni, l'utiliser pour construire le host
        tenant_header = request.META.get('HTTP_X_TENANT_SCHEMA') or request.META.get('HTTP_X_TENANT')
        
        if tenant_header:
            # En dev local (localhost), construire {tenant}.localhost
            if 'localhost' in host or '127.0.0.1' in host:
                host = f"{tenant_header}.localhost"
            # Sinon retourner le host tel quel (le header sert juste à forcer le schéma)
        
        # Retourner le hostname complet pour la recherche dans la base de données
        return host