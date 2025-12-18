from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import TenantProvisioningSerializer
from django.conf import settings
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from .models import Company, Domain
from .serializers import CompanySerializer, DomainSerializer
from django.db import connection

class CompanyViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour le modèle Company (Tenants)
    Accessible uniquement via le schéma public.
    """
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAdminUser]

class DomainReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lecture seule des Domaines.
    Accessible uniquement par les Super Admins dans le schéma public.
    """
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAdminUser]

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def current_tenant(request):
    """
    Récupère ou met à jour les informations du tenant courant.
    Accessible depuis n'importe quel schéma tenant (pas le public).
    """
    # Récupérer le tenant actuel depuis le schéma
    schema_name = connection.schema_name
    
    if schema_name == 'public':
        return Response(
            {"error": "Cette route n'est pas accessible depuis le schéma public"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Récupérer le tenant via le schema_name
        tenant = Company.objects.get(schema_name=schema_name)
        
        if request.method == 'GET':
            serializer = CompanySerializer(tenant)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        elif request.method == 'PATCH':
            # Seuls certains champs peuvent être modifiés
            allowed_fields = ['name', 'email', 'phone', 'address']
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
            
            serializer = CompanySerializer(tenant, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Company.DoesNotExist:
        return Response(
            {"error": "Tenant introuvable"},
            status=status.HTTP_404_NOT_FOUND
        )

class TenantProvisioningView(APIView):
    """
    Endpoint complet pour la création d'un nouveau tenant (Company + Domain + Admin).
    Accessible uniquement aux super-admins sur le schéma public.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = TenantProvisioningSerializer(
            data=request.data,
            context={"base_domain": settings.TENANT_BASE_DOMAIN}
        )

        if serializer.is_valid():
            try:
                result = serializer.save()
                company = result["company"]
                domain = result["domain"]
                admin_user = result["admin_user"]

                return Response({
                    "message": "Tenant créé avec succès !",
                    "company": company.name,
                    "schema_name": company.schema_name,
                    "domain": domain.domain,
                    "admin_username": admin_user.username,
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                import traceback
                traceback.print_exc()
                return Response({
                    "error": "Erreur lors de la création du tenant",
                    "details": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
