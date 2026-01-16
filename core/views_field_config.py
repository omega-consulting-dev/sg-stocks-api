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
        ]
        
        created_count = 0
        for config_data in default_configs:
            config, created = FieldConfiguration.objects.get_or_create(
                form_name=config_data['form_name'],
                field_name=config_data['field_name'],
                defaults=config_data
            )
            if created:
                created_count += 1
        
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
