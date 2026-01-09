from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from .serializers import TenantProvisioningSerializer
from django.conf import settings
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from .models import Company, Domain
from .serializers import CompanySerializer, DomainSerializer
from django.db import connection
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def renew_subscription(request):
    """
    Renouvelle l'abonnement du tenant pour 30 jours supplémentaires.
    """
    schema_name = connection.schema_name
    
    if schema_name == 'public':
        return Response(
            {"error": "Cette route n'est pas accessible depuis le schéma public"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        
        # Calculer la nouvelle date de fin
        if tenant.subscription_end_date and tenant.subscription_end_date >= timezone.now().date():
            # Si l'abonnement est encore valide, ajouter 30 jours à la date de fin actuelle
            new_end_date = tenant.subscription_end_date + timedelta(days=30)
        else:
            # Si expiré ou pas de date, partir d'aujourd'hui
            new_end_date = timezone.now().date() + timedelta(days=30)
        
        tenant.subscription_end_date = new_end_date
        tenant.last_payment_date = timezone.now().date()
        tenant.next_billing_date = new_end_date
        tenant.save()
        
        return Response({
            "message": "Abonnement renouvelé avec succès",
            "subscription_end_date": new_end_date,
            "days_added": 30
        }, status=status.HTTP_200_OK)
    
    except Company.DoesNotExist:
        return Response(
            {"error": "Tenant introuvable"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_plan(request):
    """
    Change le plan d'abonnement du tenant.
    """
    schema_name = connection.schema_name
    
    if schema_name == 'public':
        return Response(
            {"error": "Cette route n'est pas accessible depuis le schéma public"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    new_plan = request.data.get('plan')
    if not new_plan:
        return Response(
            {"error": "Le paramètre 'plan' est requis"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    valid_plans = ['starter', 'business', 'enterprise', 'custom']
    if new_plan not in valid_plans:
        return Response(
            {"error": f"Plan invalide. Choisissez parmi: {', '.join(valid_plans)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        old_plan = tenant.plan
        
        # Définir les limites et features selon le plan
        plan_configs = {
            'starter': {
                'max_users': 3,
                'max_stores': 1,
                'max_products': 1000,
                'max_storage_mb': 1000,
                'monthly_price': Decimal('15000.00'),
                'feature_services': False,
                'feature_multi_store': False,
                'feature_loans': False,
                'feature_advanced_analytics': False,
                'feature_api_access': False,
            },
            'business': {
                'max_users': 10,
                'max_stores': 5,
                'max_products': 999999,  # Illimité
                'max_storage_mb': 10000,
                'monthly_price': Decimal('35000.00'),
                'feature_services': True,
                'feature_multi_store': True,
                'feature_loans': True,
                'feature_advanced_analytics': True,
                'feature_api_access': False,
            },
            'enterprise': {
                'max_users': 999999,  # Illimité
                'max_stores': 999999,  # Illimité
                'max_products': 999999,  # Illimité
                'max_storage_mb': 999999,  # Illimité
                'monthly_price': Decimal('75000.00'),
                'feature_services': True,
                'feature_multi_store': True,
                'feature_loans': True,
                'feature_advanced_analytics': True,
                'feature_api_access': True,
            },
        }
        
        if new_plan != 'custom':
            config = plan_configs.get(new_plan)
            if config:
                tenant.plan = new_plan
                tenant.max_users = config['max_users']
                tenant.max_stores = config['max_stores']
                tenant.max_products = config['max_products']
                tenant.max_storage_mb = config['max_storage_mb']
                tenant.monthly_price = config['monthly_price']
                tenant.feature_services = config['feature_services']
                tenant.feature_multi_store = config['feature_multi_store']
                tenant.feature_loans = config['feature_loans']
                tenant.feature_advanced_analytics = config['feature_advanced_analytics']
                tenant.feature_api_access = config['feature_api_access']
                tenant.save()
        else:
            # Plan custom nécessite une configuration manuelle
            tenant.plan = 'custom'
            tenant.save()
        
        return Response({
            "message": f"Plan changé de {old_plan} à {new_plan} avec succès",
            "old_plan": old_plan,
            "new_plan": new_plan,
            "monthly_price": float(tenant.monthly_price)
        }, status=status.HTTP_200_OK)
    
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
