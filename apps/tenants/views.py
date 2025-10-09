from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import TenantProvisioningSerializer
from django.conf import settings
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from .models import Company, Domain
from .serializers import CompanySerializer, DomainSerializer

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

class TenantProvisioningView(APIView):
    """
    Endpoint pour la création et le provisioning d'un nouveau Tenant.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):

        base_domain = settings.TENANT_BASE_DOMAIN
        serializer = TenantProvisioningSerializer(
            data=request.data, 
            context={'base_domain': base_domain}
        )
        
        if serializer.is_valid():
            try:
                tenant = serializer.save()
                
                # execution des migration dans le schema
                from django_tenants.utils import schema_context
                from django.core.management import call_command

                with schema_context(tenant.schema_name):
                    call_command('migrate_schemas', schema_name=tenant.schema_name, verbosity=0)


                return Response({
                    "message": "Tenant créé et provisionné avec succès.",
                    "schema_name": tenant.schema_name,
                    "domain": f"{tenant.schema_name}.{base_domain}"
                }, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response({
                    "error": "Erreur lors du provisioning du tenant.", 
                    "details": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    