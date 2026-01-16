"""
Script to initialize default field configurations.
Run this after migration: python init_field_configs.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from core.models_field_config import FieldConfiguration

def init_field_configurations():
    """Initialize default field configurations."""
    
    default_configs = [
        # Product form
        {'form_name': 'product', 'field_name': 'name', 'field_label': 'Nom du produit', 'is_visible': True, 'is_required': True, 'display_order': 1},
        {'form_name': 'product', 'field_name': 'reference', 'field_label': 'Référence', 'is_visible': True, 'is_required': False, 'display_order': 2},
        {'form_name': 'product', 'field_name': 'category', 'field_label': 'Catégorie', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'product', 'field_name': 'purchase_price', 'field_label': "Prix d'achat", 'is_visible': True, 'is_required': False, 'display_order': 4},
        {'form_name': 'product', 'field_name': 'sale_price', 'field_label': 'Prix de vente', 'is_visible': True, 'is_required': True, 'display_order': 5},
        {'form_name': 'product', 'field_name': 'minimum_stock', 'field_label': 'Stock minimum', 'is_visible': True, 'is_required': False, 'display_order': 6},
        {'form_name': 'product', 'field_name': 'description', 'field_label': 'Description', 'is_visible': True, 'is_required': False, 'display_order': 7},
        {'form_name': 'product', 'field_name': 'barcode', 'field_label': 'Code-barres', 'is_visible': True, 'is_required': False, 'display_order': 8},
        
        # Customer form
        {'form_name': 'customer', 'field_name': 'name', 'field_label': 'Nom du client', 'is_visible': True, 'is_required': True, 'display_order': 1},
        {'form_name': 'customer', 'field_name': 'email', 'field_label': 'Email', 'is_visible': True, 'is_required': False, 'display_order': 2},
        {'form_name': 'customer', 'field_name': 'phone', 'field_label': 'Téléphone', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'customer', 'field_name': 'address', 'field_label': 'Adresse', 'is_visible': True, 'is_required': False, 'display_order': 4},
        {'form_name': 'customer', 'field_name': 'customer_type', 'field_label': 'Type de client', 'is_visible': True, 'is_required': False, 'display_order': 5},
        
        # Supplier form
        {'form_name': 'supplier', 'field_name': 'name', 'field_label': 'Nom du fournisseur', 'is_visible': True, 'is_required': True, 'display_order': 1},
        {'form_name': 'supplier', 'field_name': 'email', 'field_label': 'Email', 'is_visible': True, 'is_required': False, 'display_order': 2},
        {'form_name': 'supplier', 'field_name': 'phone', 'field_label': 'Téléphone', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'supplier', 'field_name': 'address', 'field_label': 'Adresse', 'is_visible': True, 'is_required': False, 'display_order': 4},
    ]
    
    created_count = 0
    updated_count = 0
    
    for config_data in default_configs:
        config, created = FieldConfiguration.objects.get_or_create(
            form_name=config_data['form_name'],
            field_name=config_data['field_name'],
            defaults=config_data
        )
        
        if created:
            created_count += 1
            print(f"[OK] Créé: {config}")
        else:
            # Update existing if needed
            for key, value in config_data.items():
                setattr(config, key, value)
            config.save()
            updated_count += 1
            print(f"[UPDATE] Mis à jour: {config}")
    
    print(f"\n{'='*60}")
    print(f"[STATS] Résumé:")
    print(f"   • Configurations créées: {created_count}")
    print(f"   • Configurations mises à jour: {updated_count}")
    print(f"   • Total: {len(default_configs)}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    print("[DEBUT] Initialisation des configurations de champs...\n")
    init_field_configurations()
    print("[TERMINE] Terminé!")
