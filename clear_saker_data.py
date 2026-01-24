#!/usr/bin/env python
"""
Script pour vider toutes les données du tenant saker sans supprimer le tenant
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import connection
from django_tenants.utils import schema_context

def clear_saker_data():
    """Vide toutes les données du tenant saker sans supprimer le tenant"""
    
    schema_name = 'saker'
    
    print(f"\n🔍 Connexion au tenant: {schema_name}")
    
    # Confirmation
    confirmation = input("⚠️  ATTENTION: Cette action supprimera TOUTES les données du tenant 'saker' (mais conservera le tenant). Continuer? (oui/non): ")
    if confirmation.lower() != 'oui':
        print("❌ Opération annulée.")
        return False
    
    try:
        connection.set_schema(schema_name)
        
        # Liste des modèles à vider (dans l'ordre pour respecter les foreign keys)
        # On commence par les tables dépendantes et on finit par les tables principales
        
        tables_to_clear = [
            # Paiements et transactions
            ('apps.invoicing.models', 'InvoicePayment'),
            ('apps.invoicing.models', 'InvoiceLine'),
            ('apps.invoicing.models', 'Invoice'),
            
            # Prêts
            ('apps.loans.models', 'LoanPayment'),
            ('apps.loans.models', 'Loan'),
            
            # Ventes
            ('apps.sales.models', 'SaleItem'),
            ('apps.sales.models', 'Sale'),
            
            # Mouvements de stock
            ('apps.inventory.models', 'StockMovement'),
            ('apps.inventory.models', 'StockAdjustment'),
            ('apps.inventory.models', 'StockTransfer'),
            
            # Stock produits
            ('apps.products.models', 'ProductStock'),
            ('apps.products.models', 'Product'),
            ('apps.products.models', 'Category'),
            
            # Dépenses
            ('apps.expenses.models', 'Expense'),
            ('apps.expenses.models', 'ExpenseCategory'),
            
            # Caisse
            ('apps.cashbox.models', 'CashboxTransaction'),
            ('apps.cashbox.models', 'Cashbox'),
            
            # Clients et fournisseurs
            ('apps.customers.models', 'Customer'),
            ('apps.suppliers.models', 'Supplier'),
            
            # Magasins (optionnel - décommenter si nécessaire)
            # ('apps.main.models', 'Store'),
        ]
        
        total_deleted = 0
        
        for module_path, model_name in tables_to_clear:
            try:
                # Importer le modèle dynamiquement
                module = __import__(module_path, fromlist=[model_name])
                model = getattr(module, model_name)
                
                count = model.objects.count()
                if count > 0:
                    deleted, _ = model.objects.all().delete()
                    print(f"🗑️  {model_name}: {deleted} enregistrement(s) supprimé(s)")
                    total_deleted += deleted
                else:
                    print(f"✓  {model_name}: déjà vide")
                    
            except Exception as e:
                print(f"⚠️  {model_name}: Erreur - {str(e)}")
        
        print(f"\n✅ Opération terminée ! {total_deleted} enregistrement(s) supprimé(s) au total.")
        print(f"📌 Le tenant 'saker' est maintenant vide mais toujours actif.")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    clear_saker_data()
