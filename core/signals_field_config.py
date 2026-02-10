"""
Signal handlers for automatic field configuration initialization
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_tenants.utils import schema_context
from apps.tenants.models import Company
from core.models_field_config import FieldConfiguration
from core.field_config_defaults import get_default_field_configurations
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Company)
def initialize_field_configurations_for_new_tenant(sender, instance, created, **kwargs):
    """
    Automatically initialize field configurations when a new tenant is created.
    This signal fires after a Company (tenant) is saved.
    """
    if created and instance.schema_name != 'public':
        logger.info(f"🔧 Initializing field configurations for new tenant: {instance.schema_name}")
        
        try:
            with schema_context(instance.schema_name):
                # Vérifier d'abord si la table existe
                from django.db import connection
                table_exists = False
                
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = %s 
                                AND table_name = 'core_fieldconfiguration'
                            );
                        """, [instance.schema_name])
                        table_exists = cursor.fetchone()[0]
                except Exception as check_error:
                    logger.warning(f" Could not check if table exists for {instance.schema_name}: {str(check_error)}")
                    return
                
                if not table_exists:
                    logger.info(f" Table core_fieldconfiguration does not exist yet for tenant {instance.schema_name}. Skipping initialization (will be done after migrations).")
                    return
                
                # Check if configurations already exist
                existing_count = FieldConfiguration.objects.count()
                
                if existing_count == 0:
                    # No configurations exist, create them
                    default_configs = get_default_field_configurations()
                    created_configs = []
                    
                    for config_data in default_configs:
                        config = FieldConfiguration.objects.create(**config_data)
                        created_configs.append(config)
                    
                    logger.info(f" Created {len(created_configs)} field configurations for tenant {instance.schema_name}")
                else:
                    # Configurations exist, check if all expected forms are present
                    default_configs = get_default_field_configurations()
                    expected_forms = set(config['form_name'] for config in default_configs)
                    existing_forms = set(FieldConfiguration.objects.values_list('form_name', flat=True).distinct())
                    missing_forms = expected_forms - existing_forms
                    
                    if missing_forms:
                        logger.info(f"📝 Adding missing form configurations for tenant {instance.schema_name}: {missing_forms}")
                        
                        # Add only missing configurations
                        added_count = 0
                        for config_data in default_configs:
                            if config_data['form_name'] in missing_forms:
                                FieldConfiguration.objects.get_or_create(
                                    form_name=config_data['form_name'],
                                    field_name=config_data['field_name'],
                                    defaults=config_data
                                )
                                added_count += 1
                        
                        logger.info(f" Added {added_count} missing field configurations for tenant {instance.schema_name}")
                    else:
                        logger.info(f"ℹ All field configurations already exist for tenant {instance.schema_name}")
                        
        except Exception as e:
            logger.error(f" Error initializing field configurations for tenant {instance.schema_name}: {str(e)}")
