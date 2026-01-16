#!/usr/bin/env python
"""
Initialiser les configurations par défaut dans chaque tenant
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model
from core.models_field_config import FieldConfiguration

# Configurations par défaut pour les produits
DEFAULT_CONFIGS = [
    # Formulaire Produit
    {'form_name': 'product', 'field_name': 'name', 'field_label': 'Nom', 'is_visible': True, 'is_required': True, 'display_order': 1},
    {'form_name': 'product', 'field_name': 'reference', 'field_label': 'Référence', 'is_visible': True, 'is_required': False, 'display_order': 2},
    {'form_name': 'product', 'field_name': 'category', 'field_label': 'Catégorie', 'is_visible': True, 'is_required': False, 'display_order': 3},
    {'form_name': 'product', 'field_name': 'description', 'field_label': 'Description', 'is_visible': True, 'is_required': False, 'display_order': 4},
    {'form_name': 'product', 'field_name': 'barcode', 'field_label': 'Code-barres', 'is_visible': True, 'is_required': False, 'display_order': 5},
    {'form_name': 'product', 'field_name': 'purchase_price', 'field_label': "Prix d'achat", 'is_visible': True, 'is_required': False, 'display_order': 6},
    {'form_name': 'product', 'field_name': 'sale_price', 'field_label': 'Prix de vente', 'is_visible': True, 'is_required': True, 'display_order': 7},
    {'form_name': 'product', 'field_name': 'minimum_stock', 'field_label': 'Stock minimum', 'is_visible': True, 'is_required': False, 'display_order': 8},
    
    # Tableau Produit (colonnes)
    {'form_name': 'product_table', 'field_name': 'image', 'field_label': 'Image', 'is_visible': True, 'is_required': False, 'display_order': 1},
    {'form_name': 'product_table', 'field_name': 'code', 'field_label': 'Code', 'is_visible': True, 'is_required': False, 'display_order': 2},
    {'form_name': 'product_table', 'field_name': 'designation', 'field_label': 'Désignation', 'is_visible': True, 'is_required': False, 'display_order': 3},
    {'form_name': 'product_table', 'field_name': 'family', 'field_label': 'Famille', 'is_visible': True, 'is_required': False, 'display_order': 4},
    {'form_name': 'product_table', 'field_name': 'purchase_price', 'field_label': 'Prix Achat', 'is_visible': False, 'is_required': False, 'display_order': 5},
    {'form_name': 'product_table', 'field_name': 'sale_price', 'field_label': 'Prix Vente', 'is_visible': True, 'is_required': False, 'display_order': 6},
    {'form_name': 'product_table', 'field_name': 'minimum_stock', 'field_label': 'Stock Min', 'is_visible': True, 'is_required': False, 'display_order': 7},
    {'form_name': 'product_table', 'field_name': 'optimal_stock', 'field_label': 'Stock Opt', 'is_visible': True, 'is_required': False, 'display_order': 8},
    {'form_name': 'product_table', 'field_name': 'current_stock', 'field_label': 'Stock Actuel', 'is_visible': True, 'is_required': False, 'display_order': 9},
    
    # Formulaire Service
    {'form_name': 'service', 'field_name': 'name', 'field_label': 'Nom', 'is_visible': True, 'is_required': True, 'display_order': 1},
    {'form_name': 'service', 'field_name': 'reference', 'field_label': 'Référence', 'is_visible': True, 'is_required': False, 'display_order': 2},
    {'form_name': 'service', 'field_name': 'category', 'field_label': 'Catégorie', 'is_visible': True, 'is_required': True, 'display_order': 3},
    {'form_name': 'service', 'field_name': 'description', 'field_label': 'Description', 'is_visible': True, 'is_required': False, 'display_order': 4},
    {'form_name': 'service', 'field_name': 'unit_price', 'field_label': 'Prix unitaire', 'is_visible': True, 'is_required': True, 'display_order': 5},
    {'form_name': 'service', 'field_name': 'tax_rate', 'field_label': 'Taux TVA', 'is_visible': True, 'is_required': False, 'display_order': 6},
    {'form_name': 'service', 'field_name': 'estimated_duration', 'field_label': 'Durée estimée', 'is_visible': True, 'is_required': False, 'display_order': 7},
    
    # Tableau Service (colonnes)
    {'form_name': 'service_table', 'field_name': 'reference', 'field_label': 'Référence', 'is_visible': True, 'is_required': False, 'display_order': 1},
    {'form_name': 'service_table', 'field_name': 'name', 'field_label': 'Nom', 'is_visible': True, 'is_required': False, 'display_order': 2},
    {'form_name': 'service_table', 'field_name': 'category', 'field_label': 'Catégorie', 'is_visible': True, 'is_required': False, 'display_order': 3},
    {'form_name': 'service_table', 'field_name': 'unit_price', 'field_label': 'Prix unitaire', 'is_visible': True, 'is_required': False, 'display_order': 4},
    {'form_name': 'service_table', 'field_name': 'tax_rate', 'field_label': 'TVA', 'is_visible': True, 'is_required': False, 'display_order': 5},
    {'form_name': 'service_table', 'field_name': 'estimated_duration', 'field_label': 'Durée', 'is_visible': True, 'is_required': False, 'display_order': 6},
    
    # Formulaire Achat (Entrée Stock)
    {'form_name': 'purchase', 'field_name': 'receipt_number', 'field_label': 'N° Pièce', 'is_visible': True, 'is_required': True, 'display_order': 1},
    {'form_name': 'purchase', 'field_name': 'store', 'field_label': 'Magasin', 'is_visible': True, 'is_required': True, 'display_order': 2},
    {'form_name': 'purchase', 'field_name': 'supplier', 'field_label': 'Fournisseur', 'is_visible': True, 'is_required': False, 'display_order': 3},
    {'form_name': 'purchase', 'field_name': 'reference', 'field_label': 'Référence livraison', 'is_visible': True, 'is_required': False, 'display_order': 4},
    {'form_name': 'purchase', 'field_name': 'date', 'field_label': 'Date', 'is_visible': True, 'is_required': True, 'display_order': 5},
    {'form_name': 'purchase', 'field_name': 'notes', 'field_label': 'Intitulé/Notes', 'is_visible': True, 'is_required': False, 'display_order': 6},
    {'form_name': 'purchase', 'field_name': 'invoice_amount', 'field_label': 'Montant facture', 'is_visible': True, 'is_required': False, 'display_order': 7},
    {'form_name': 'purchase', 'field_name': 'unit_cost', 'field_label': 'Prix unitaire', 'is_visible': True, 'is_required': False, 'display_order': 8},
    {'form_name': 'purchase', 'field_name': 'payment_amount', 'field_label': 'Montant versé', 'is_visible': True, 'is_required': False, 'display_order': 9},
    {'form_name': 'purchase', 'field_name': 'payment_method', 'field_label': 'Nature paiement', 'is_visible': True, 'is_required': False, 'display_order': 10},
    {'form_name': 'purchase', 'field_name': 'due_date', 'field_label': 'Date limite règlement', 'is_visible': True, 'is_required': False, 'display_order': 11},
    
    # Tableau Achat (Entrée Stock) - colonnes
    {'form_name': 'purchase_table', 'field_name': 'receipt_number', 'field_label': 'N° Pièce', 'is_visible': True, 'is_required': False, 'display_order': 1},
    {'form_name': 'purchase_table', 'field_name': 'reference', 'field_label': 'Référence', 'is_visible': True, 'is_required': False, 'display_order': 2},
    {'form_name': 'purchase_table', 'field_name': 'product_name', 'field_label': 'Produit', 'is_visible': True, 'is_required': False, 'display_order': 3},
    {'form_name': 'purchase_table', 'field_name': 'store_name', 'field_label': 'Magasin', 'is_visible': True, 'is_required': False, 'display_order': 4},
    {'form_name': 'purchase_table', 'field_name': 'quantity', 'field_label': 'Quantité', 'is_visible': True, 'is_required': False, 'display_order': 5},
    {'form_name': 'purchase_table', 'field_name': 'invoice_amount', 'field_label': 'Montant facture', 'is_visible': True, 'is_required': False, 'display_order': 6},
    {'form_name': 'purchase_table', 'field_name': 'created_at', 'field_label': 'Date', 'is_visible': True, 'is_required': False, 'display_order': 7},
    
    # Formulaire Facture (Invoice)
    {'form_name': 'invoice', 'field_name': 'customer', 'field_label': 'Client', 'is_visible': True, 'is_required': False, 'display_order': 1},
    {'form_name': 'invoice', 'field_name': 'saleDate', 'field_label': 'Date de vente', 'is_visible': True, 'is_required': True, 'display_order': 2},
    {'form_name': 'invoice', 'field_name': 'paymentMethod', 'field_label': 'Méthode de paiement', 'is_visible': True, 'is_required': False, 'display_order': 3},
    {'form_name': 'invoice', 'field_name': 'paymentTerm', 'field_label': 'Conditions de paiement', 'is_visible': True, 'is_required': False, 'display_order': 4},
    {'form_name': 'invoice', 'field_name': 'amountPaid', 'field_label': 'Montant payé', 'is_visible': True, 'is_required': False, 'display_order': 5},
    {'form_name': 'invoice', 'field_name': 'tax', 'field_label': 'TVA (%)', 'is_visible': True, 'is_required': False, 'display_order': 6},
    {'form_name': 'invoice', 'field_name': 'acompte', 'field_label': 'Acompte', 'is_visible': True, 'is_required': False, 'display_order': 7},
    {'form_name': 'invoice', 'field_name': 'notes', 'field_label': 'Notes', 'is_visible': True, 'is_required': False, 'display_order': 8},
    {'form_name': 'invoice', 'field_name': 'dueDate', 'field_label': 'Date d\'échéance', 'is_visible': True, 'is_required': False, 'display_order': 9},
]

print("\n" + "=" * 70)
print("Initialisation des configurations par défaut")
print("=" * 70)

Tenant = get_tenant_model()
tenants = Tenant.objects.exclude(schema_name='public').all()

for tenant in tenants:
    connection.set_tenant(tenant)
    print(f"\n[PACKAGE] Tenant: {tenant.schema_name.upper()}")
    
    # Supprimer les anciennes configs (si elles existent)
    deleted_count = FieldConfiguration.objects.all().delete()[0]
    if deleted_count > 0:
        print(f"  [ATTENTION]  {deleted_count} ancienne(s) configuration(s) supprimée(s)")
    
    # Créer les nouvelles configs
    created_configs = []
    for config_data in DEFAULT_CONFIGS:
        config = FieldConfiguration.objects.create(**config_data)
        created_configs.append(config)
    
    print(f"  ✓ {len(created_configs)} configuration(s) créée(s)")
    
    # Vérifier
    total = FieldConfiguration.objects.count()
    print(f"  ✓ Total dans ce tenant: {total} configurations")

print("\n" + "=" * 70)
print("[OK] Terminé! Chaque tenant a ses propres configurations")
print("=" * 70)
