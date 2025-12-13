from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import HasModulePermission
from drf_spectacular.utils import extend_schema, extend_schema_view
from apps.main.models_settings import CompanySettings
from apps.main.serializers_settings import CompanySettingsSerializer


@extend_schema_view(
    list=extend_schema(summary="Obtenir la configuration d'entreprise", tags=["Settings"]),
    update=extend_schema(summary="Mettre à jour la configuration", tags=["Settings"]),
    partial_update=extend_schema(summary="Mise à jour partielle de la configuration", tags=["Settings"]),
)
class CompanySettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for company settings (singleton).
    Only one settings instance exists.
    """
    
    queryset = CompanySettings.objects.all()
    serializer_class = CompanySettingsSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'patch', 'post', 'delete']  # Allow POST and DELETE for actions
    
    def list(self, request, *args, **kwargs):
        """Get the company settings (singleton)."""
        settings = CompanySettings.get_settings()
        serializer = self.get_serializer(settings, context={'request': request})
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Get the company settings by ID."""
        settings = CompanySettings.get_settings()
        serializer = self.get_serializer(settings, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update company settings."""
        settings = CompanySettings.get_settings()
        serializer = self.get_serializer(
            settings, 
            data=request.data, 
            partial=kwargs.get('partial', False),
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """Partial update of company settings."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def upload_logo(self, request):
        """Upload company logo."""
        settings = CompanySettings.get_settings()
        
        if 'logo' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier logo fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        settings.logo = request.FILES['logo']
        settings.save()
        
        serializer = self.get_serializer(settings, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'])
    def remove_logo(self, request):
        """Remove company logo."""
        settings = CompanySettings.get_settings()
        
        if settings.logo:
            settings.logo.delete()
            settings.save()
        
        serializer = self.get_serializer(settings, context={'request': request})
        return Response(serializer.data)
