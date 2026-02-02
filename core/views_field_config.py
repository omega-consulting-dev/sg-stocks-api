"""
Views for field configuration management.
"""

import logging
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
from core.field_config_defaults import get_default_field_configurations

logger = logging.getLogger(__name__)


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
    
    def list(self, request, *args, **kwargs):
        """Override list to auto-initialize configurations if they don't exist."""
        # Check if configurations exist
        if not FieldConfiguration.objects.exists():
            # Auto-initialize default configurations
            default_configs = get_default_field_configurations()
            created_count = 0
            
            for config_data in default_configs:
                FieldConfiguration.objects.get_or_create(
                    form_name=config_data['form_name'],
                    field_name=config_data['field_name'],
                    defaults=config_data
                )
                created_count += 1
            
            logger.info(f"✅ Auto-initialized {created_count} field configurations")
        
        return super().list(request, *args, **kwargs)
    
    @extend_schema(summary="Initialiser les configurations par défaut", tags=["Settings"])
    @action(detail=False, methods=['post'])
    def initialize_defaults(self, request):
        """Initialize default field configurations for all forms."""
        
        # Get force parameter to decide whether to update existing configs
        force = request.data.get('force', False)
        
        # Get default configurations from centralized source
        default_configs = get_default_field_configurations()
        
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
