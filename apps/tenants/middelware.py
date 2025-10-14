from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import remove_www


class TenantHeaderMiddleware(TenantMainMiddleware):
    """
    Middleware pour récupérer le domain du tenant via l'en-tête 'X-Tenant'.
    """
    @staticmethod
    def hostname_from_request(request):
        tenant_header = request.META.get('HTTP_X_TENANT')
        host = remove_www(request.get_host().split(':')[0])

        if tenant_header:
            host_ = host.split('.')
            if len(host_) == 1:
                host = '.'.join([tenant_header, host_[0]])
        
        return host