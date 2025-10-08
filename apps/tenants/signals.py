from django.db.models.signals import post_migrate
from django.dispatch import receiver
from apps.tenants.models import Company, Domain
from myproject.config.env import get_env

@receiver(post_migrate)
def create_public_tenant(sender, **kwargs):
    if Company.objects.filter(schema_name='public').exists():
        return

    public_tenant = Company.objects.create(
        schema_name='public',
        name='Public Tenant'
    )
    Domain.objects.create(
        domain=get_env('BASE_DOMAIN'),
        tenant=public_tenant,
        is_primary=True
    )
