"""
Vues pour la gestion de l'inscription publique et la création de tenants.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from django_tenants.utils import schema_context
from apps.main.models import User as PublicUser
from apps.tenants.models import Company, Domain
from apps.accounts.models import User as TenantUser, Role
from apps.main.tasks import send_registration_confirmation_email
from decimal import Decimal
from datetime import date, timedelta
import re


@api_view(['POST'])
@permission_classes([AllowAny])
def check_email(request):
    """
    Vérifie si un email existe déjà dans le système (tous les tenants).
    Retourne { exists: true/false, message: "..." }
    """
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response({
            'error': 'Email requis'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validation basique du format email
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})?$'
    if not re.match(email_regex, email):
        return Response({
            'error': 'Format d\'email invalide'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Vérifier si l'email existe dans le schéma public
    if PublicUser.objects.filter(email=email).exists():
        return Response({
            'exists': True,
            'email': email,
            'message': 'Cet email existe déjà. Connectez-vous.'
        })
    
    # Vérifier si l'email existe dans n'importe quel tenant
    from apps.tenants.models import Company
    tenants = Company.objects.exclude(schema_name='public')
    
    for tenant in tenants:
        with schema_context(tenant.schema_name):
            if TenantUser.objects.filter(email=email).exists():
                return Response({
                    'exists': True,
                    'email': email,
                    'message': 'Cet email existe déjà. Connectez-vous.'
                })
    
    return Response({
        'exists': False,
        'email': email,
        'message': 'Email disponible. Vous pouvez créer un compte.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def register_tenant(request):
    """
    Inscription complète : crée l'utilisateur, le tenant (entreprise) et configure l'abonnement.
    
    Données attendues:
    {
        "user": {
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "password": "SecurePass123",
            "password_confirm": "SecurePass123"
        },
        "company": {
            "name": "Mon Entreprise",
            "schema_name": "monentreprise",  # Auto-généré si absent
            "domain": "monentreprise.localhost",  # Auto-généré si absent
            "phone": "+237123456789",
            "address": "Douala, Cameroun"
        },
        "subscription": {
            "pack_id": 1,  # ID du pack choisi
            "payment_method": "mobile_money"
        }
    }
    """
    user_data = request.data.get('user', {})
    company_data = request.data.get('company', {})
    subscription_data = request.data.get('subscription', {})
    
    # Récupérer le plan sélectionné (starter, business, enterprise)
    selected_plan = company_data.get('plan', 'starter')
    
    # DEBUG: Afficher les données reçues
    print("=" * 80)
    print("DONNÉES REÇUES POUR L'INSCRIPTION:")
    print(f"Plan reçu dans company_data: {company_data.get('plan')}")
    print(f"Plan sélectionné: {selected_plan}")
    print(f"Subscription data: {subscription_data}")
    print("=" * 80)
    
    # Configuration des plans
    plan_configs = {
        'starter': {
            'first_payment': Decimal('229900.00'),
            'renewal': Decimal('100000.00'),
            'trial_days': 14,
            'duration': 365,
            'max_users': 10,
            'max_stores': 1,
            'max_warehouses': 0,
            'max_products': 999999,
            'max_storage_mb': 15360,
            'feature_services': True,
            'feature_multi_store': False,
            'feature_loans': False,
            'feature_advanced_analytics': False,
            'feature_api_access': False,
        },
        'business': {
            'first_payment': Decimal('449900.00'),
            'renewal': Decimal('150000.00'),
            'trial_days': 14,
            'duration': 365,
            'max_users': 15,
            'max_stores': 1,
            'max_warehouses': 1,
            'max_products': 999999,
            'max_storage_mb': 30720,
            'feature_services': True,
            'feature_multi_store': True,
            'feature_loans': True,
            'feature_advanced_analytics': True,
            'feature_api_access': False,
        },
        'enterprise': {
            'first_payment': Decimal('699900.00'),
            'renewal': Decimal('250000.00'),
            'trial_days': 14,
            'duration': 365,
            'max_users': 999999,
            'max_stores': 999999,
            'max_warehouses': 999999,
            'max_products': 999999,
            'max_storage_mb': 51200,
            'feature_services': True,
            'feature_multi_store': True,
            'feature_loans': True,
            'feature_advanced_analytics': True,
            'feature_api_access': True,
        }
    }
    
    plan_config = plan_configs.get(selected_plan, plan_configs['starter'])
    
    # Validation
    errors = {}
    
    # Vérifier les données utilisateur
    if not user_data.get('email'):
        errors['email'] = 'Email requis'
    else:
        # Validation du format email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})?$'
        if not re.match(email_regex, user_data.get('email')):
            errors['email'] = 'Format d\'email invalide'
    
    if not user_data.get('first_name'):
        errors['first_name'] = 'Prénom requis'
    elif len(user_data.get('first_name', '').strip()) < 2:
        errors['first_name'] = 'Le prénom doit contenir au moins 2 caractères'
    
    if not user_data.get('last_name'):
        errors['last_name'] = 'Nom requis'
    elif len(user_data.get('last_name', '').strip()) < 2:
        errors['last_name'] = 'Le nom doit contenir au moins 2 caractères'
    
    if not user_data.get('password'):
        errors['password'] = 'Mot de passe requis'
    elif len(user_data.get('password', '')) < 6:
        errors['password'] = 'Le mot de passe doit contenir au moins 6 caractères'
    
    if user_data.get('password') != user_data.get('password_confirm'):
        errors['password_confirm'] = 'Les mots de passe ne correspondent pas'
    
    # Vérifier si l'email existe déjà dans le schéma public
    if not errors.get('email') and PublicUser.objects.filter(email=user_data.get('email')).exists():
        errors['email'] = 'Cet email est déjà utilisé'
    
    # Vérifier si l'email existe dans n'importe quel tenant
    if not errors.get('email'):
        tenants = Company.objects.exclude(schema_name='public')
        for tenant in tenants:
            with schema_context(tenant.schema_name):
                if TenantUser.objects.filter(email=user_data.get('email')).exists():
                    errors['email'] = 'Cet email est déjà utilisé'
                    break
    
    # Vérifier les données entreprise
    if not company_data.get('name'):
        errors['company_name'] = 'Nom de l\'entreprise requis'
    elif len(company_data.get('name', '').strip()) < 2:
        errors['company_name'] = 'Le nom de l\'entreprise doit contenir au moins 2 caractères'
    
    # Vérifier le sous-domaine
    subdomain = company_data.get('subdomain', '').strip()
    if not subdomain:
        errors['subdomain'] = 'Sous-domaine requis'
    elif len(subdomain) < 3:
        errors['subdomain'] = 'Le sous-domaine doit contenir au moins 3 caractères'
    elif ' ' in subdomain:
        errors['subdomain'] = 'Le sous-domaine ne peut pas contenir d\'espaces'
    elif not re.match(r'^[a-z0-9_-]+$', subdomain):
        errors['subdomain'] = 'Le sous-domaine doit contenir uniquement des lettres minuscules, chiffres, tiret (-) et underscore (_)'
    elif subdomain.startswith(('-', '_')) or subdomain.endswith(('-', '_')):
        errors['subdomain'] = 'Le sous-domaine ne peut pas commencer ou finir par - ou _'
    
    # Vérifier si le sous-domaine existe déjà
    if not errors.get('subdomain'):
        schema_name = f"standard_{company_data['subdomain']}"
        if Company.objects.filter(schema_name=schema_name).exists():
            errors['subdomain'] = 'Ce sous-domaine est déjà utilisé. Veuillez en choisir un autre.'
    
    if not company_data.get('address'):
        errors['company_address'] = 'Adresse professionnelle requise'
    elif len(company_data.get('address', '').strip()) < 5:
        errors['company_address'] = 'L\'adresse doit contenir au moins 5 caractères'
    
    if not company_data.get('phone'):
        errors['company_phone'] = 'Numéro de téléphone requis'
    elif len(company_data.get('phone', '').replace('+237', '').strip()) < 8:
        errors['company_phone'] = 'Le numéro de téléphone doit contenir au moins 8 chiffres'
    
    # Vérifier les données d'abonnement
    if not subscription_data.get('payment_method'):
        errors['payment_method'] = 'Méthode de paiement requise'
    elif subscription_data.get('payment_method') not in ['card', 'orange', 'mobile']:
        errors['payment_method'] = 'Méthode de paiement invalide'
    
    if errors:
        return Response({
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 1. Créer le tenant (Client/Entreprise)
        company_name = company_data['name']
        subdomain = company_data['subdomain']
        
        # Utiliser le sous-domaine fourni par l'utilisateur
        schema_name = f"standard_{subdomain}"
        
        # Créer le tenant
        from datetime import date, timedelta
        tenant = Company.objects.create(
            schema_name=schema_name,
            name=company_name,
            email=user_data['email'],
            phone=company_data.get('phone', ''),
            address=company_data.get('address', ''),
            plan=selected_plan,  # Utiliser le plan sélectionné
            # Configuration de la tarification selon le pack choisi
            first_payment_price=plan_config['first_payment'],
            renewal_price=plan_config['renewal'],
            subscription_duration_days=plan_config['duration'],
            trial_days=plan_config['trial_days'],
            is_first_payment=True,  # C'est le premier paiement
            # Dates d'abonnement
            trial_end_date=date.today() + timedelta(days=plan_config['trial_days']),
            subscription_end_date=date.today() + timedelta(days=plan_config['trial_days'] + plan_config['duration']),
            is_active=True,
            # Limites selon le plan
            max_users=plan_config['max_users'],
            max_stores=plan_config['max_stores'],
            max_warehouses=plan_config['max_warehouses'],
            max_products=plan_config['max_products'],
            max_storage_mb=plan_config['max_storage_mb'],
            # Features selon le plan
            feature_services=plan_config['feature_services'],
            feature_multi_store=plan_config['feature_multi_store'],
            feature_loans=plan_config['feature_loans'],
            feature_advanced_analytics=plan_config['feature_advanced_analytics'],
            feature_api_access=plan_config['feature_api_access'],
        )
        
        # 2. Créer le domaine
        # Production :
        # domain_name = f"{subdomain}.sgstocks.com"
        
        # Local (décommenter pour les tests locaux) :
        domain_name = f"{subdomain}.localhost"
        
        Domain.objects.create(
            domain=domain_name,
            tenant=tenant,
            is_primary=True
        )
        
        # 3. Créer l'utilisateur principal dans le schéma public
        user = PublicUser.objects.create_user(
            username=user_data['email'].split('@')[0],
            email=user_data['email'],
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            is_staff=False,
            is_superuser=False
        )
        user.set_password(user_data['password'])
        user.save()
        
        # 4. Créer l'utilisateur dans le schéma du tenant (SUPER ADMIN)
        with schema_context(tenant.schema_name):
            # Créer ou récupérer le rôle super_admin
            super_admin_role, created = Role.objects.get_or_create(
                name='super_admin',
                defaults={
                    'display_name': 'Super Administrateur',
                    'description': 'Accès complet à toutes les fonctionnalités',
                    'can_manage_users': True,
                    'can_manage_products': True,
                    'can_view_products': True,
                    'can_manage_categories': True,
                    'can_view_categories': True,
                    'can_manage_services': True,
                    'can_view_services': True,
                    'can_manage_inventory': True,
                    'can_view_inventory': True,
                    'can_manage_sales': True,
                    'can_manage_customers': True,
                    'can_manage_suppliers': True,
                    'can_manage_cashbox': True,
                    'can_manage_bank': True,
                    'can_manage_loans': True,
                    'can_manage_expenses': True,
                    'can_view_analytics': True,
                    'can_export_data': True,
                    'access_scope': 'all',
                }
            )
            
            # Créer l'utilisateur avec le rôle super_admin
            tenant_user = TenantUser.objects.create_user(
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_staff=True,
                is_superuser=True,
                role=super_admin_role  # Assigner le rôle
            )
            tenant_user.set_password(user_data['password'])
            tenant_user.save()
            tenant_user.save()
        
        # 5. Gestion du paiement (à intégrer avec MTN/Orange Money API)
        payment_method = subscription_data.get('payment_method')
        payment_amount = plan_config['first_payment']
        
        # TODO: Intégrer l'API de paiement MTN/Orange
        # if payment_method == 'orange':
        #     # Appel API Orange Money pour le montant
        # elif payment_method == 'mobile':
        #     # Appel API MTN Mobile Money pour le montant
        
        # 6. Construire l'URL d'accès à l'application
        # Production :
        # access_url = f"http://{subdomain}.sgstocks.com"
        
        # Local (décommenter pour les tests locaux) :
        access_url = f"http://{subdomain}.localhost:5173"
        
        # 7. Envoyer email de confirmation en arrière-plan avec Celery
        try:
            # Préparer les données pour la tâche asynchrone
            user_data_email = {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'password': user_data['password']  # Inclure le mot de passe pour l'email
            }
            
            company_data_email = {
                'name': tenant.name,
                'schema_name': tenant.schema_name,
                'domain_name': domain_name,
                'plan': selected_plan
            }
            
            subscription_data_email = {
                'payment_amount': float(payment_amount),
                'trial_days': plan_config['trial_days'],
                'duration': plan_config['duration'],
                'renewal_price': float(plan_config['renewal']),
                'subscription_end_date': tenant.subscription_end_date.strftime('%d/%m/%Y'),
                'access_url': access_url
            }
            
            # Envoyer l'email en arrière-plan (asynchrone)
            send_registration_confirmation_email.delay(
                user_data=user_data_email,
                company_data=company_data_email,
                subscription_data=subscription_data_email
            )
            
        except Exception as e:
            # Logger l'erreur mais ne pas bloquer l'inscription
            print(f"Erreur lors de l'envoi de la tâche email: {e}")
        
        # 8. Retourner la réponse de succès
        
        return Response({
            'success': True,
            'message': 'Inscription réussie ! Votre entreprise a été créée.',
            'data': {
                'user': {
                    'email': user.email,
                    'name': f"{user.first_name} {user.last_name}"
                },
                'company': {
                    'name': tenant.name,
                    'domain': domain_name,
                    'schema': tenant.schema_name,
                    'plan': selected_plan,
                    'amount_paid': float(payment_amount),
                    'trial_days': plan_config['trial_days'],
                    'subscription_end': tenant.subscription_end_date.strftime('%Y-%m-%d')
                },
                'access_url': access_url
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Erreur lors de l\'inscription: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
