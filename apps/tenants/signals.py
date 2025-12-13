from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django_tenants.utils import tenant_context
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


@receiver(post_save, sender=Company)
def create_default_roles(sender, instance, created, **kwargs):
    """
    Créer automatiquement les rôles par défaut lors de la création d'un nouveau tenant.
    """
    if not created or instance.schema_name == 'public':
        return
    
    # Import ici pour éviter les imports circulaires
    from apps.accounts.models import Role
    
    # Créer les rôles dans le contexte du tenant
    with tenant_context(instance):
        # Définir tous les rôles par défaut
        default_roles = [
            {
                'name': 'super_admin',
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
            },
            {
                'name': 'manager',
                'display_name': 'Gérant/Directeur',
                'description': 'Accès complet aux opérations quotidiennes',
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
            },
            {
                'name': 'store_manager',
                'display_name': 'Responsable Point de Vente',
                'description': 'Gestion d\'un point de vente',
                'can_manage_users': False,
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
                'can_manage_suppliers': False,
                'can_manage_cashbox': True,
                'can_manage_loans': True,
                'can_manage_expenses': True,
                'can_view_analytics': True,
                'can_export_data': True,
                'access_scope': 'assigned',
            },
            {
                'name': 'cashier',
                'display_name': 'Caissier',
                'description': 'Gestion des ventes et de la caisse',
                'can_manage_users': False,
                'can_manage_products': False,
                'can_view_products': True,
                'can_manage_categories': False,
                'can_view_categories': True,
                'can_manage_services': False,
                'can_view_services': True,
                'can_manage_inventory': False,
                'can_view_inventory': True,
                'can_manage_sales': True,
                'can_manage_customers': False,
                'can_manage_suppliers': False,
                'can_manage_cashbox': True,
                'can_manage_loans': False,
                'can_manage_expenses': False,
                'can_view_analytics': False,
                'can_export_data': False,
                'access_scope': 'assigned',
            },
            {
                'name': 'salesperson',
                'display_name': 'Vendeur',
                'description': 'Gestion des ventes',
                'can_manage_users': False,
                'can_manage_products': False,
                'can_view_products': True,
                'can_manage_categories': False,
                'can_view_categories': True,
                'can_manage_services': False,
                'can_view_services': True,
                'can_manage_inventory': False,
                'can_view_inventory': True,
                'can_manage_sales': True,
                'can_manage_customers': True,
                'can_manage_suppliers': False,
                'can_manage_cashbox': False,
                'can_manage_loans': False,
                'can_manage_expenses': False,
                'can_view_analytics': False,
                'can_export_data': False,
                'access_scope': 'assigned',
            },
        ]
        
        for role_data in default_roles:
            Role.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
