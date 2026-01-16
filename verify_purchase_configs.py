"""
Script pour vérifier que les configurations d'achats (purchase) sont bien créées
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model
from core.models_field_config import FieldConfiguration

print("\n" + "=" * 80)
print("VÉRIFICATION DES CONFIGURATIONS D'ACHATS")
print("=" * 80)

Tenant = get_tenant_model()
tenants = Tenant.objects.exclude(schema_name='public').all()

for tenant in tenants:
    connection.set_tenant(tenant)
    print(f"\n📦 Tenant: {tenant.schema_name.upper()}")
    print("-" * 80)
    
    # Configurations du formulaire Achats
    purchase_form_configs = FieldConfiguration.objects.filter(
        form_name='purchase'
    ).order_by('display_order')
    
    print(f"\n   FORMULAIRE ACHATS ({purchase_form_configs.count()} champs):")
    for config in purchase_form_configs:
        visible = "✅" if config.is_visible else "❌"
        required = "⭐" if config.is_required else "  "
        print(f"   {visible} {required} {config.field_label:<25} ({config.field_name})")
    
    # Configurations du tableau Achats
    purchase_table_configs = FieldConfiguration.objects.filter(
        form_name='purchase_table'
    ).order_by('display_order')
    
    print(f"\n   TABLEAU ACHATS ({purchase_table_configs.count()} colonnes):")
    for config in purchase_table_configs:
        visible = "✅" if config.is_visible else "❌"
        print(f"   {visible}  {config.field_label:<25} ({config.field_name})")
    
    print()

print("=" * 80)
print("\nLégende:")
print("  ✅ = Visible")
print("  ❌ = Caché")
print("  ⭐ = Obligatoire")
print("\n" + "=" * 80)
