"""
Middleware for WebSocket tenant handling.
"""
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django_tenants.utils import get_tenant_model, get_tenant_domain_model
from django.db import connection


@database_sync_to_async
def get_tenant_from_host(hostname):
    """Get tenant from hostname."""
    try:
        TenantModel = get_tenant_model()
        DomainModel = get_tenant_domain_model()
        
        # Remove port if present
        hostname = hostname.split(':')[0]
        
        # Try to find domain
        domain = DomainModel.objects.select_related('tenant').get(domain=hostname)
        return domain.tenant
    except DomainModel.DoesNotExist:
        # Fallback to public schema
        return None


class TenantWebSocketMiddleware:
    """
    Middleware to set tenant context for WebSocket connections.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Get hostname from headers
        headers = dict(scope.get('headers', []))
        host = headers.get(b'host', b'').decode()
        
        if not host:
            host = scope.get('server', ['localhost'])[0]
        
        # Get tenant
        tenant = await get_tenant_from_host(host)
        
        if tenant:
            # Set tenant in scope for consumer
            scope['tenant'] = tenant
        
        return await self.app(scope, receive, send)
