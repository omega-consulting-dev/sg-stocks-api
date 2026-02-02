"""
Default field configurations - centralized configuration
"""

def get_default_field_configurations():
    """
    Returns the list of default field configurations for all forms.
    This is used both by the API endpoint and by signals.
    """
    return [
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
        {'form_name': 'purchase_table', 'field_name': 'supplier_name', 'field_label': 'Fournisseur', 'is_visible': True, 'is_required': False, 'display_order': 5},
        {'form_name': 'purchase_table', 'field_name': 'quantity', 'field_label': 'Quantité', 'is_visible': True, 'is_required': False, 'display_order': 6},
        {'form_name': 'purchase_table', 'field_name': 'invoice_amount', 'field_label': 'Montant facture', 'is_visible': True, 'is_required': False, 'display_order': 7},
        {'form_name': 'purchase_table', 'field_name': 'created_at', 'field_label': 'Date', 'is_visible': True, 'is_required': False, 'display_order': 8},
        
        # Customer form
        {'form_name': 'customer', 'field_name': 'name', 'field_label': 'Nom / Raison sociale', 'is_visible': True, 'is_required': True, 'display_order': 1},
        {'form_name': 'customer', 'field_name': 'email', 'field_label': 'Email', 'is_visible': True, 'is_required': False, 'display_order': 2},
        {'form_name': 'customer', 'field_name': 'phone', 'field_label': 'Téléphone', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'customer', 'field_name': 'mobile', 'field_label': 'Mobile', 'is_visible': True, 'is_required': False, 'display_order': 4},
        {'form_name': 'customer', 'field_name': 'address', 'field_label': 'Adresse', 'is_visible': True, 'is_required': False, 'display_order': 5},
        {'form_name': 'customer', 'field_name': 'city', 'field_label': 'Ville', 'is_visible': True, 'is_required': False, 'display_order': 6},
        {'form_name': 'customer', 'field_name': 'postal_code', 'field_label': 'Code postal', 'is_visible': True, 'is_required': False, 'display_order': 7},
        {'form_name': 'customer', 'field_name': 'country', 'field_label': 'Pays', 'is_visible': True, 'is_required': False, 'display_order': 8},
        {'form_name': 'customer', 'field_name': 'billing_address', 'field_label': 'Adresse de facturation', 'is_visible': True, 'is_required': False, 'display_order': 9},
        {'form_name': 'customer', 'field_name': 'tax_id', 'field_label': 'Numéro fiscal', 'is_visible': True, 'is_required': False, 'display_order': 10},
        {'form_name': 'customer', 'field_name': 'payment_term', 'field_label': 'Conditions de paiement', 'is_visible': True, 'is_required': False, 'display_order': 11},
        {'form_name': 'customer', 'field_name': 'credit_limit', 'field_label': 'Limite de crédit', 'is_visible': True, 'is_required': False, 'display_order': 12},
        {'form_name': 'customer', 'field_name': 'notes', 'field_label': 'Notes', 'is_visible': True, 'is_required': False, 'display_order': 13},
        
        # Supplier form
        {'form_name': 'supplier', 'field_name': 'name', 'field_label': 'Raison sociale', 'is_visible': True, 'is_required': True, 'display_order': 1},
        {'form_name': 'supplier', 'field_name': 'contact_person', 'field_label': 'Contact principal', 'is_visible': True, 'is_required': False, 'display_order': 2},
        {'form_name': 'supplier', 'field_name': 'email', 'field_label': 'Email', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'supplier', 'field_name': 'phone', 'field_label': 'Téléphone', 'is_visible': True, 'is_required': False, 'display_order': 4},
        {'form_name': 'supplier', 'field_name': 'mobile', 'field_label': 'Mobile', 'is_visible': True, 'is_required': False, 'display_order': 5},
        {'form_name': 'supplier', 'field_name': 'website', 'field_label': 'Site web', 'is_visible': True, 'is_required': False, 'display_order': 6},
        {'form_name': 'supplier', 'field_name': 'address', 'field_label': 'Adresse', 'is_visible': True, 'is_required': False, 'display_order': 7},
        {'form_name': 'supplier', 'field_name': 'city', 'field_label': 'Ville', 'is_visible': True, 'is_required': False, 'display_order': 8},
        {'form_name': 'supplier', 'field_name': 'postal_code', 'field_label': 'Code postal', 'is_visible': True, 'is_required': False, 'display_order': 9},
        {'form_name': 'supplier', 'field_name': 'country', 'field_label': 'Pays', 'is_visible': True, 'is_required': False, 'display_order': 10},
        {'form_name': 'supplier', 'field_name': 'tax_id', 'field_label': 'Numéro fiscal', 'is_visible': True, 'is_required': False, 'display_order': 11},
        {'form_name': 'supplier', 'field_name': 'bank_account', 'field_label': 'Compte bancaire', 'is_visible': True, 'is_required': False, 'display_order': 12},
        {'form_name': 'supplier', 'field_name': 'payment_term', 'field_label': 'Conditions de paiement', 'is_visible': True, 'is_required': False, 'display_order': 13},
        {'form_name': 'supplier', 'field_name': 'rating', 'field_label': 'Évaluation', 'is_visible': True, 'is_required': False, 'display_order': 14},
        {'form_name': 'supplier', 'field_name': 'notes', 'field_label': 'Notes', 'is_visible': True, 'is_required': False, 'display_order': 15},
        
        # Invoice (product) form
        {'form_name': 'invoice', 'field_name': 'customer', 'field_label': 'Client', 'is_visible': True, 'is_required': True, 'display_order': 1},
        {'form_name': 'invoice', 'field_name': 'saleDate', 'field_label': 'Date de vente', 'is_visible': True, 'is_required': True, 'display_order': 2},
        {'form_name': 'invoice', 'field_name': 'paymentMethod', 'field_label': 'Mode de paiement', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'invoice', 'field_name': 'paymentTerm', 'field_label': 'Terme de paiement', 'is_visible': True, 'is_required': False, 'display_order': 4},
        {'form_name': 'invoice', 'field_name': 'tax', 'field_label': 'TVA (%)', 'is_visible': True, 'is_required': False, 'display_order': 5},
        {'form_name': 'invoice', 'field_name': 'amountPaid', 'field_label': 'Montant payé', 'is_visible': True, 'is_required': False, 'display_order': 6},
        {'form_name': 'invoice', 'field_name': 'acompte', 'field_label': 'Acompte', 'is_visible': True, 'is_required': False, 'display_order': 7},
        {'form_name': 'invoice', 'field_name': 'dueDate', 'field_label': "Date d'échéance", 'is_visible': True, 'is_required': False, 'display_order': 8},
        {'form_name': 'invoice', 'field_name': 'notes', 'field_label': 'Notes', 'is_visible': True, 'is_required': False, 'display_order': 9},
        
        # Invoice Service form
        {'form_name': 'invoice_service', 'field_name': 'customer', 'field_label': 'Client', 'is_visible': True, 'is_required': True, 'display_order': 1},
        {'form_name': 'invoice_service', 'field_name': 'saleDate', 'field_label': 'Date de vente', 'is_visible': True, 'is_required': True, 'display_order': 2},
        {'form_name': 'invoice_service', 'field_name': 'paymentMethod', 'field_label': 'Mode de paiement', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'invoice_service', 'field_name': 'paymentTerm', 'field_label': 'Terme de paiement', 'is_visible': True, 'is_required': False, 'display_order': 4},
        {'form_name': 'invoice_service', 'field_name': 'tax', 'field_label': 'TVA (%)', 'is_visible': True, 'is_required': False, 'display_order': 5},
        {'form_name': 'invoice_service', 'field_name': 'amountPaid', 'field_label': 'Montant payé', 'is_visible': True, 'is_required': False, 'display_order': 6},
        {'form_name': 'invoice_service', 'field_name': 'acompte', 'field_label': 'Acompte', 'is_visible': True, 'is_required': False, 'display_order': 7},
        {'form_name': 'invoice_service', 'field_name': 'dueDate', 'field_label': "Date d'échéance", 'is_visible': True, 'is_required': False, 'display_order': 8},
        {'form_name': 'invoice_service', 'field_name': 'notes', 'field_label': 'Notes', 'is_visible': True, 'is_required': False, 'display_order': 9},
        
        # Loan form
        {'form_name': 'loan', 'field_name': 'loan_type', 'field_label': "Type d'emprunt", 'is_visible': True, 'is_required': True, 'display_order': 1},
        {'form_name': 'loan', 'field_name': 'lender_name', 'field_label': 'Nom du prêteur', 'is_visible': True, 'is_required': True, 'display_order': 2},
        {'form_name': 'loan', 'field_name': 'lender_contact', 'field_label': 'Contact prêteur', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'loan', 'field_name': 'store', 'field_label': 'Point de vente', 'is_visible': True, 'is_required': False, 'display_order': 4},
        {'form_name': 'loan', 'field_name': 'principal_amount', 'field_label': 'Montant emprunté', 'is_visible': True, 'is_required': True, 'display_order': 5},
        {'form_name': 'loan', 'field_name': 'interest_rate', 'field_label': "Taux d'intérêt (%)", 'is_visible': True, 'is_required': True, 'display_order': 6},
        {'form_name': 'loan', 'field_name': 'duration_months', 'field_label': 'Durée (mois)', 'is_visible': True, 'is_required': True, 'display_order': 7},
        {'form_name': 'loan', 'field_name': 'start_date', 'field_label': 'Date de début', 'is_visible': True, 'is_required': True, 'display_order': 8},
        {'form_name': 'loan', 'field_name': 'end_date', 'field_label': 'Date de fin', 'is_visible': True, 'is_required': True, 'display_order': 9},
        {'form_name': 'loan', 'field_name': 'purpose', 'field_label': 'Objet du prêt', 'is_visible': True, 'is_required': False, 'display_order': 10},
        {'form_name': 'loan', 'field_name': 'notes', 'field_label': 'Notes', 'is_visible': True, 'is_required': False, 'display_order': 11},
        
        # Loan table
        {'form_name': 'loan_table', 'field_name': 'loan_number', 'field_label': 'N° Emprunt', 'is_visible': True, 'is_required': False, 'display_order': 1},
        {'form_name': 'loan_table', 'field_name': 'lender_name', 'field_label': 'Prêteur', 'is_visible': True, 'is_required': False, 'display_order': 2},
        {'form_name': 'loan_table', 'field_name': 'loan_type', 'field_label': 'Type', 'is_visible': True, 'is_required': False, 'display_order': 3},
        {'form_name': 'loan_table', 'field_name': 'start_date', 'field_label': 'Date', 'is_visible': True, 'is_required': False, 'display_order': 4},
        {'form_name': 'loan_table', 'field_name': 'principal_amount', 'field_label': 'Montant Principal', 'is_visible': True, 'is_required': False, 'display_order': 5},
        {'form_name': 'loan_table', 'field_name': 'interest_rate', 'field_label': 'Taux (%)', 'is_visible': True, 'is_required': False, 'display_order': 6},
        {'form_name': 'loan_table', 'field_name': 'balance_due', 'field_label': 'Solde Restant', 'is_visible': True, 'is_required': False, 'display_order': 7},
        {'form_name': 'loan_table', 'field_name': 'status', 'field_label': 'Statut', 'is_visible': True, 'is_required': False, 'display_order': 8},
    ]
