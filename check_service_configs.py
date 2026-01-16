import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django_tenants.utils import schema_context
from core.models import FieldConfiguration

with schema_context('demo'):
    configs = FieldConfiguration.objects.filter(
        form_name__in=['service', 'service_table']
    ).order_by('form_name', 'display_order')
    
    print(f'\n=== CONFIGURATIONS SERVICE (DEMO) ===')
    print(f'Total: {configs.count()}')
    
    print('\nFORMULAIRE SERVICE:')
    for c in configs.filter(form_name='service'):
        print(f'  {c.field_name}: {c.field_label} (visible={c.is_visible}, required={c.is_required})')
    
    print('\nTABLEAU SERVICE:')
    for c in configs.filter(form_name='service_table'):
        print(f'  {c.field_name}: {c.field_label} (visible={c.is_visible})')
