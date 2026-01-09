from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import HasModulePermission
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.conf import settings as django_settings
from django.utils.translation import activate, get_language
from apps.main.models_settings import CompanySettings
from apps.main.serializers_settings import CompanySettingsSerializer


@extend_schema(
    summary="Obtenir les langues disponibles",
    tags=["Settings"],
    responses={200: {
        'type': 'object',
        'properties': {
            'languages': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'code': {'type': 'string'},
                        'name': {'type': 'string'}
                    }
                }
            },
            'current': {'type': 'string'}
        }
    }}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_languages(request):
    """Get available languages."""
    languages = [
        {'code': code, 'name': name}
        for code, name in django_settings.LANGUAGES
    ]
    current_language = get_language()
    
    return Response({
        'languages': languages,
        'current': current_language
    })


@extend_schema(
    summary="Changer la langue",
    tags=["Settings"],
    request={
        'type': 'object',
        'properties': {
            'language': {'type': 'string', 'enum': ['fr', 'en']}
        }
    },
    responses={200: {
        'type': 'object',
        'properties': {
            'language': {'type': 'string'},
            'message': {'type': 'string'}
        }
    }}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_language(request):
    """Set user language preference."""
    from django.utils import translation
    
    language = request.data.get('language')
    
    if not language:
        return Response(
            {'error': 'Language code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate language code
    available_languages = [code for code, name in django_settings.LANGUAGES]
    if language not in available_languages:
        return Response(
            {'error': f'Language not supported. Available: {", ".join(available_languages)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Activate language for this request
    translation.activate(language)
    
    # Save to session - Django uses '_language' as the session key
    request.session['_language'] = language
    request.session.modified = True
    
    # Create response
    response = Response({
        'language': language,
        'message': f'Language changed to {language}'
    })
    
    # Also set language cookie for better persistence
    response.set_cookie(
        django_settings.LANGUAGE_COOKIE_NAME,
        language,
        max_age=django_settings.LANGUAGE_COOKIE_AGE,
        path=django_settings.LANGUAGE_COOKIE_PATH,
        domain=django_settings.LANGUAGE_COOKIE_DOMAIN,
        secure=django_settings.LANGUAGE_COOKIE_SECURE,
        httponly=django_settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=django_settings.LANGUAGE_COOKIE_SAMESITE,
    )
    
    return response


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
