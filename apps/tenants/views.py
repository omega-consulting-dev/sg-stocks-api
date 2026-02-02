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
            allowed_fields = ['name', 'email', 'phone', 'address', 'allow_flexible_pricing']
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
    Renouvelle l'abonnement du tenant.
    Utilise subscription_duration_days et gère le passage de is_first_payment à False.
    Note: Cette route ne devrait être appelée qu'après validation du paiement.
    """
    schema_name = connection.schema_name
    
    if schema_name == 'public':
        return Response(
            {"error": "Cette route n'est pas accessible depuis le schéma public"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        
        # Calculer le nombre de jours à ajouter
        duration_days = tenant.subscription_duration_days or 365
        
        # Calculer la nouvelle date de fin
        if tenant.subscription_end_date and tenant.subscription_end_date >= timezone.now().date():
            # Si l'abonnement est encore valide, ajouter à la date de fin actuelle
            new_end_date = tenant.subscription_end_date + timedelta(days=duration_days)
        else:
            # Si expiré ou pas de date, partir d'aujourd'hui
            new_end_date = timezone.now().date() + timedelta(days=duration_days)
        
        # Marquer que ce n'est plus le premier paiement après le renouvellement
        was_first_payment = tenant.is_first_payment
        if tenant.is_first_payment:
            tenant.is_first_payment = False
        
        tenant.subscription_end_date = new_end_date
        tenant.last_payment_date = timezone.now().date()
        tenant.next_billing_date = new_end_date
        
        # Réactiver le compte si suspendu pour cause d'expiration
        if tenant.is_suspended and "expir" in (tenant.suspension_reason or "").lower():
            tenant.is_suspended = False
            tenant.suspension_reason = None
        
        tenant.save()
        
        return Response({
            "message": "Abonnement renouvelé avec succès",
            "subscription_end_date": new_end_date,
            "days_added": duration_days,
            "was_first_payment": was_first_payment,
            "is_now_renewal": not tenant.is_first_payment,
            "next_price": float(tenant.renewal_price if tenant.renewal_price > 0 else tenant.get_plan_price())
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
        # Prix basés sur les packs : PACK 1 (Starter), PACK 2 (Business), PACK 3 (Enterprise)
        plan_configs = {
            'starter': {
                'max_users': 10,
                'max_stores': 1,  # 1 point de vente uniquement
                'max_warehouses': 0,  # Pas de magasin/entrepôt
                'max_products': 999999,  # Illimité
                'max_storage_mb': 15360,  # 15 Go
                'first_payment_price': Decimal('229900.00'),  # PACK 1 - 1ère année
                'renewal_price': Decimal('100000.00'),  # PACK 1 - renouvellement
                'monthly_price': Decimal('229900.00'),  # Prix par défaut (1ère année)
                'feature_services': True,
                'feature_multi_store': False,
                'feature_loans': True,
                'feature_advanced_analytics': True,
                'feature_api_access': True,
            },
            'business': {
                'max_users': 15,
                'max_stores': 1,  # 1 point de vente
                'max_warehouses': 1,  # 1 magasin/entrepôt
                'max_products': 999999,  # Illimité
                'max_storage_mb': 30720,  # 30 Go
                'first_payment_price': Decimal('449900.00'),  # PACK 2 - 1ère année
                'renewal_price': Decimal('150000.00'),  # PACK 2 - renouvellement
                'monthly_price': Decimal('449900.00'),  # Prix par défaut (1ère année)
                'feature_services': True,
                'feature_multi_store': True,
                'feature_loans': True,
                'feature_advanced_analytics': True,
                'feature_api_access': True,
            },
            'enterprise': {
                'max_users': 999999,  # Illimité
                'max_stores': 999999,  # Illimité
                'max_warehouses': 999999,  # Illimité
                'max_products': 999999,  # Illimité
                'max_storage_mb': 51200,  # 50 Go
                'first_payment_price': Decimal('699900.00'),  # PACK 3 - 1ère année
                'renewal_price': Decimal('250000.00'),  # PACK 3 - renouvellement
                'monthly_price': Decimal('699900.00'),  # Prix par défaut (1ère année)
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
                tenant.max_warehouses = config['max_warehouses']
                tenant.max_products = config['max_products']
                tenant.max_storage_mb = config['max_storage_mb']
                tenant.monthly_price = config['monthly_price']
                tenant.first_payment_price = config['first_payment_price']
                tenant.renewal_price = config['renewal_price']
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
        
        # Calculer le prix actuel à payer (selon si c'est le premier paiement ou un renouvellement)
        current_price = tenant.first_payment_price if tenant.is_first_payment else tenant.renewal_price
        
        return Response({
            "message": f"Plan changé de {old_plan} à {new_plan} avec succès",
            "old_plan": old_plan,
            "new_plan": new_plan,
            "current_price": float(current_price),
            "first_payment_price": float(tenant.first_payment_price),
            "renewal_price": float(tenant.renewal_price),
            "is_first_payment": tenant.is_first_payment
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription_price(request):
    """
    Retourne le montant à payer pour l'abonnement actuel.
    Prend en compte si c'est le premier paiement ou un renouvellement.
    """
    schema_name = connection.schema_name
    
    if schema_name == 'public':
        return Response(
            {"error": "Cette route n'est pas accessible depuis le schéma public"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        
        # Calculer le prix actuel
        current_price = tenant.get_current_price()
        
        # Informations de réduction
        reduction_percentage = 0
        if tenant.first_payment_price > 0 and tenant.renewal_price > 0:
            reduction_percentage = ((tenant.first_payment_price - tenant.renewal_price) / tenant.first_payment_price) * 100
        
        return Response({
            "plan": tenant.plan,
            "plan_name": dict(Company.PLAN_CHOICES).get(tenant.plan, tenant.plan),
            "is_first_payment": tenant.is_first_payment,
            "current_price": float(current_price),
            "first_payment_price": float(tenant.first_payment_price),
            "renewal_price": float(tenant.renewal_price),
            "reduction_percentage": round(reduction_percentage, 2),
            "subscription_duration_days": tenant.subscription_duration_days,
            "trial_days": tenant.trial_days,
            "subscription_end_date": tenant.subscription_end_date,
            "is_subscription_expired": tenant.is_subscription_expired(),
            "days_until_expiration": tenant.days_until_expiration(),
            "currency": tenant.currency
        }, status=status.HTTP_200_OK)
    
    except Company.DoesNotExist:
        return Response(
            {"error": "Tenant introuvable"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_payment(request):
    """
    Valide un paiement et prolonge l'abonnement.
    Cette route doit être appelée après confirmation du paiement.
    
    Attendu dans request.data:
    - payment_reference: Référence du paiement
    - amount: Montant payé
    - payment_method: Méthode de paiement (mobile_money, card, bank_transfer, etc.)
    """
    schema_name = connection.schema_name
    
    if schema_name == 'public':
        return Response(
            {"error": "Cette route n'est pas accessible depuis le schéma public"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    payment_reference = request.data.get('payment_reference')
    amount = request.data.get('amount')
    payment_method = request.data.get('payment_method', 'unknown')
    
    if not payment_reference or not amount:
        return Response(
            {"error": "payment_reference et amount sont requis"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        return Response(
            {"error": "Le montant doit être un nombre valide"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        
        # Vérifier le montant attendu
        expected_amount = tenant.get_current_price()
        
        # Tolérance de 1% pour les arrondis ou frais
        tolerance = expected_amount * Decimal('0.01')
        if amount < (expected_amount - tolerance):
            return Response({
                "error": "Montant insuffisant",
                "expected_amount": float(expected_amount),
                "received_amount": float(amount),
                "difference": float(expected_amount - amount)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculer la nouvelle date de fin
        duration_days = tenant.subscription_duration_days or 365
        
        if tenant.subscription_end_date and tenant.subscription_end_date >= timezone.now().date():
            new_end_date = tenant.subscription_end_date + timedelta(days=duration_days)
        else:
            new_end_date = timezone.now().date() + timedelta(days=duration_days)
        
        # Enregistrer le paiement
        was_first_payment = tenant.is_first_payment
        if tenant.is_first_payment:
            tenant.is_first_payment = False
        
        tenant.subscription_end_date = new_end_date
        tenant.last_payment_date = timezone.now().date()
        tenant.next_billing_date = new_end_date
        
        # Réactiver le compte si suspendu
        if tenant.is_suspended and "expir" in (tenant.suspension_reason or "").lower():
            tenant.is_suspended = False
            tenant.suspension_reason = None
        
        tenant.save()
        
        # TODO: Enregistrer le paiement dans un modèle Payment pour historique
        # Payment.objects.create(
        #     tenant=tenant,
        #     reference=payment_reference,
        #     amount=amount,
        #     payment_method=payment_method,
        #     ...
        # )
        
        return Response({
            "message": "Paiement validé et abonnement renouvelé avec succès",
            "payment_reference": payment_reference,
            "amount_paid": float(amount),
            "was_first_payment": was_first_payment,
            "is_now_renewal": not tenant.is_first_payment,
            "subscription_end_date": new_end_date,
            "days_added": duration_days,
            "next_price": float(tenant.renewal_price if tenant.renewal_price > 0 else tenant.get_plan_price())
        }, status=status.HTTP_200_OK)
    
    except Company.DoesNotExist:
        return Response(
            {"error": "Tenant introuvable"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    """
    Retourne le statut détaillé de l'abonnement du tenant.
    """
    schema_name = connection.schema_name
    
    if schema_name == 'public':
        return Response(
            {"error": "Cette route n'est pas accessible depuis le schéma public"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tenant = Company.objects.get(schema_name=schema_name)
        
        days_until_expiration = tenant.days_until_expiration()
        is_expired = tenant.is_subscription_expired()
        
        # Statut
        if is_expired:
            status_text = "expired"
        elif days_until_expiration and days_until_expiration <= 7:
            status_text = "expiring_soon"
        elif days_until_expiration and days_until_expiration <= 30:
            status_text = "active_expiring"
        else:
            status_text = "active"
        
        return Response({
            "status": status_text,
            "plan": tenant.plan,
            "plan_name": dict(Company.PLAN_CHOICES).get(tenant.plan, tenant.plan),
            "is_active": tenant.is_active,
            "is_suspended": tenant.is_suspended,
            "suspension_reason": tenant.suspension_reason,
            "subscription_end_date": tenant.subscription_end_date,
            "is_subscription_expired": is_expired,
            "days_until_expiration": days_until_expiration,
            "last_payment_date": tenant.last_payment_date,
            "next_billing_date": tenant.next_billing_date,
            "current_price": float(tenant.get_current_price()),
            "is_first_payment": tenant.is_first_payment,
            "limits": {
                "max_users": tenant.max_users,
                "max_stores": tenant.max_stores,
                "max_warehouses": tenant.max_warehouses,
                "max_products": tenant.max_products,
                "max_storage_mb": tenant.max_storage_mb
            },
            "usage": {
                "total_users_count": tenant.total_users_count,
                "storage_used_mb": tenant.storage_used_mb,
                "total_products_count": tenant.total_products_count
            }
        }, status=status.HTTP_200_OK)
    
    except Company.DoesNotExist:
        return Response(
            {"error": "Tenant introuvable"},
            status=status.HTTP_404_NOT_FOUND
        )
