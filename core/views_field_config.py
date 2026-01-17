"""
Views for field configuration management.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from core.models_field_config import FieldConfiguration
from core.serializers_field_config import (
    FieldConfigurationSerializer,
    FieldConfigurationBulkUpdateSerializer
)


@extend_schema_view(
    list=extend_schema(summary="Liste des configurations de champs", tags=["Settings"]),
    retrieve=extend_schema(summary="Détail d'une configuration", tags=["Settings"]),
    create=extend_schema(summary="Créer une configuration", tags=["Settings"]),
    update=extend_schema(summary="Modifier une configuration", tags=["Settings"]),
    partial_update=extend_schema(summary="Modifier partiellement une configuration", tags=["Settings"]),
)
class FieldConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing field configurations."""
    
    queryset = FieldConfiguration.objects.all()
    serializer_class = FieldConfigurationSerializer
    permission_classes = [AllowAny]  # Temporairement pour tester
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['form_name', 'is_visible', 'is_required']
    
    @extend_schema(summary="Initialiser les configurations par défaut", tags=["Settings"])
    @action(detail=False, methods=['post'])
    def initialize_defaults(self, request):
        """Initialize default field configurations for all forms."""
        
        # Get force parameter to decide whether to update existing configs
        force = request.data.get('force', False)
        
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
        
        created_count = 0
        updated_count = 0
        
        for config_data in default_configs:
            if force:
                # Update or create: mise à jour des configs existantes
                config, created = FieldConfiguration.objects.update_or_create(
                    form_name=config_data['form_name'],
                    field_name=config_data['field_name'],
                    defaults={
                        'field_label': config_data['field_label'],
                        'is_visible': config_data['is_visible'],
                        'is_required': config_data['is_required'],
                        'display_order': config_data['display_order']
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            else:
                # Get or create: ne crée que les nouvelles
                config, created = FieldConfiguration.objects.get_or_create(
                    form_name=config_data['form_name'],
                    field_name=config_data['field_name'],
                    defaults=config_data
                )
                if created:
                    created_count += 1
        
        if force:
            return Response({
                'message': f'{created_count} configurations créées, {updated_count} mises à jour',
                'total': len(default_configs)
            })
        else:
            return Response({
                'message': f'{created_count} configurations créées',
                'total': len(default_configs)
            })
    
    @extend_schema(summary="Mise à jour en masse des configurations", tags=["Settings"])
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update field configurations."""
        
        serializer = FieldConfigurationBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_count = 0
        errors = []
        
        for config_data in serializer.validated_data['configurations']:
            config_id = config_data.pop('id')
            try:
                config = FieldConfiguration.objects.get(id=config_id)
                for key, value in config_data.items():
                    setattr(config, key, value)
                config.save()
                updated_count += 1
            except FieldConfiguration.DoesNotExist:
                errors.append(f"Configuration {config_id} non trouvée")
            except Exception as e:
                errors.append(f"Erreur lors de la mise à jour de {config_id}: {str(e)}")
        
        return Response({
            'message': f'{updated_count} configurations mises à jour',
            'errors': errors if errors else None
        })
    
    @extend_schema(summary="Obtenir les configurations par formulaire", tags=["Settings"])
    @action(detail=False, methods=['get'])
    def by_form(self, request):
        """Get field configurations grouped by form."""
        
        form_name = request.query_params.get('form_name')
        
        if not form_name:
            return Response(
                {'error': 'Le paramètre form_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        configs = FieldConfiguration.objects.filter(form_name=form_name)
        serializer = self.get_serializer(configs, many=True)
        
        return Response(serializer.data)
