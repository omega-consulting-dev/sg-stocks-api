from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import remove_www
import logging

logger = logging.getLogger(__name__)


class TenantHeaderMiddleware(TenantMainMiddleware):
    """
    Middleware pour récupérer le domain du tenant via l'en-tête 'X-Tenant-Schema' ou hostname.
    """
    @staticmethod
    def hostname_from_request(request):
        # Récupère le hostname depuis la requête
        raw_host = request.get_host()
        host = remove_www(raw_host.split(':')[0].lower())
        
        # Si un header X-Tenant ou X-Tenant-Schema est fourni, l'utiliser pour construire le host
        tenant_header = request.META.get('HTTP_X_TENANT_SCHEMA') or request.META.get('HTTP_X_TENANT')
        
        if tenant_header:
            # En dev local (localhost), construire {tenant}.localhost
            if 'localhost' in host or '127.0.0.1' in host:
                host = f"{tenant_header}.localhost"
            # En production, construire {tenant}.sg-stocks.com
            elif 'sg-stocks.com' in host:
                host = f"{tenant_header}.sg-stocks.com"
        
        return host