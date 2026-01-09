"""
Tâches asynchrones Celery pour le provisioning des tenants.
"""
from celery import shared_task
from django.core.management import call_command
from django_tenants.utils import connection
from apps.accounts.models import User, Role
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def provision_tenant_async(self, company_id, admin_data):
    """
    Provisionne un tenant de manière asynchrone :
    1. Exécute les migrations sur le schéma
    2. Crée les rôles par défaut
    3. Crée l'utilisateur administrateur
    
    Args:
        company_id: ID de la Company (tenant) à provisionner
        admin_data: Dict contenant les infos de l'admin (username, email, password, etc.)
    """
    from apps.tenants.models import Company
    
    try:
        company = Company.objects.get(id=company_id)
        schema_name = company.schema_name
        
        logger.info(f"🚀 Début du provisioning asynchrone pour {company.name} (schema: {schema_name})")
        
        # Étape 1: Migrations du schéma (la partie la plus longue)
        logger.info(f"⏳ Migration du schéma {schema_name}...")
        call_command('migrate_schemas', schema_name=schema_name, verbosity=0)
        logger.info(f"✅ Migrations terminées pour {schema_name}")
        
        # Étape 2: Création des rôles dans le schéma du tenant
        connection.set_tenant(company)
        
        logger.info(f"👥 Création des rôles par défaut...")
        
        # Super admin role
        super_role_defaults = {
            'display_name': 'Super Administrateur',
            'description': 'Accès total à toutes les fonctionnalités',
            'can_manage_users': True,
            'can_manage_products': True,
            'can_manage_inventory': True,
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
        
        super_admin_role, _ = Role.objects.get_or_create(
            name='super_admin',
            defaults=super_role_defaults
        )
        
        # Manager role
        Role.objects.get_or_create(
            name='manager',
            defaults={
                'display_name': 'Gérant/Directeur',
                'description': 'Accès complet aux fonctionnalités métier',
                'can_manage_users': True,
                'can_manage_products': True,
                'can_manage_inventory': True,
                'can_manage_sales': True,
                'can_manage_customers': True,
                'can_manage_suppliers': True,
                'can_manage_cashbox': True,
                'can_manage_loans': True,
                'can_manage_expenses': True,
                'can_view_analytics': True,
                'access_scope': 'all',
            }
        )
        
        logger.info(f"✅ Rôles créés")
        
        # Étape 3: Création de l'utilisateur administrateur
        logger.info(f"👤 Création de l'utilisateur admin...")
        
        admin_user = User.objects.create_user(
            username=admin_data.get("username"),
            email=admin_data.get("email"),
            password=admin_data.get("password"),
            first_name=admin_data.get("first_name", ''),
            last_name=admin_data.get("last_name", ''),
            is_staff=True,
            is_superuser=True,
            role=super_admin_role,
        )
        
        logger.info(f"✅ Utilisateur admin créé: {admin_user.username}")
        
        # Mettre à jour le statut du tenant
        company.is_active = True
        company.provisioning_status = 'completed'
        company.save(update_fields=['is_active', 'provisioning_status'])
        
        logger.info(f"🎉 Provisioning terminé avec succès pour {company.name}")
        
        return {
            'status': 'success',
            'company_id': company_id,
            'schema_name': schema_name
        }
        
    except Exception as exc:
        logger.error(f"❌ Erreur lors du provisioning de {company_id}: {str(exc)}")
        
        # Mettre à jour le statut d'erreur
        try:
            company = Company.objects.get(id=company_id)
            company.provisioning_status = 'failed'
            company.save(update_fields=['provisioning_status'])
        except:
            pass
        
        # Réessayer jusqu'à 3 fois avec un délai exponentiel
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
