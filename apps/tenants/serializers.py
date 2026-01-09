from rest_framework import serializers
from django.db import transaction
from django.core.management import call_command
from django.utils import timezone
from .models import Company, Domain, CompanyBilling, AuditLog, SupportTicket, SystemMetrics
from apps.accounts.models import User, Role

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ('id', 'domain', 'is_primary')
        read_only_fields = ('tenant',)

class CompanySerializer(serializers.ModelSerializer):
    domains = DomainSerializer(many=True, read_only=True)
    
    class Meta:
        model = Company
        fields = (
            'id', 'name', 'schema_name', 'email', 'phone', 'address',
            'plan', 'is_active', 'created_on', 'domains',
            # Subscription fields
            'max_users', 'max_stores', 'max_products', 'max_storage_mb',
            'feature_services', 'feature_multi_store', 'feature_loans',
            'feature_advanced_analytics', 'feature_api_access',
            'trial_end_date', 'subscription_end_date',
            'monthly_price', 'last_payment_date', 'next_billing_date',
            # Usage metrics
            'storage_used_mb', 'total_users_count', 'total_products_count',
            # Settings
            'currency', 'tax_rate'
        )
        read_only_fields = ('schema_name', 'created_on')


class TenantProvisioningSerializer(serializers.Serializer):
    """
    Serializer complet pour la création d'un Tenant avec toutes les informations.
    """
    # Informations de base
    name = serializers.CharField(max_length=150)
    subdomain = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    plan = serializers.ChoiceField(choices=Company.PLAN_CHOICES, default='starter')
    
    # Prix personnalisé (uniquement pour le plan 'custom')
    monthly_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Prix mensuel personnalisé (uniquement pour le plan 'custom')"
    )

    # Modules / features
    feature_services = serializers.BooleanField(default=False)
    feature_multi_store = serializers.BooleanField(default=False)
    feature_loans = serializers.BooleanField(default=False)
    feature_advanced_analytics = serializers.BooleanField(default=False)
    feature_api_access = serializers.BooleanField(default=False)

    # Compte admin
    admin_username = serializers.CharField(max_length=150)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True)
    admin_first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    admin_last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_subdomain(self, value):
        """Vérifie que le sous-domaine n'existe pas déjà et n'est pas réservé."""
        base_domain = self.context.get("base_domain")
        fqdn = f"{value}.{base_domain}"
        if Domain.objects.filter(domain=fqdn).exists():
            raise serializers.ValidationError("Ce sous-domaine est déjà utilisé.")
        if value.lower() in ["www", "admin", "api", "public"]:
            raise serializers.ValidationError("Ce sous-domaine est réservé.")
        return value
    
    def validate(self, data):
        """Validation globale pour vérifier la cohérence plan/prix."""
        plan = data.get('plan')
        monthly_price = data.get('monthly_price')
        
        # Si le plan est 'custom', le prix doit être fourni
        if plan == 'custom' and not monthly_price:
            raise serializers.ValidationError({
                'monthly_price': 'Le prix mensuel est obligatoire pour un plan personnalisé.'
            })
        
        # Si ce n'est pas un plan custom, ignorer le prix fourni
        if plan != 'custom' and monthly_price:
            data['monthly_price'] = None  # Sera calculé automatiquement
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        Crée le tenant et lance le provisioning en arrière-plan.
        Retourne immédiatement sans attendre les migrations.
        """
        from .tasks import provision_tenant_async
        
        base_domain = self.context.get("base_domain")

        # Récupérer les données
        name = validated_data["name"]
        schema_name = validated_data["subdomain"].lower()
        subdomain = validated_data["subdomain"].lower()
        plan = validated_data["plan"]

        # Déterminer les limites selon le plan
        plan_map = {
            'starter': (3, 1),
            'business': (10, 3),
            'enterprise': (25, 10)
        }
        max_users, max_stores = plan_map.get(plan, (3, 1))

        # Création du tenant (rapide - juste la table publique)
        company_data = {
            'schema_name': schema_name,
            'name': name,
            'email': validated_data.get("email"),
            'phone': validated_data.get("phone"),
            'address': validated_data.get("address"),
            'plan': plan,
            'max_users': max_users,
            'max_stores': max_stores,
            'feature_services': validated_data.get("feature_services", False),
            'feature_multi_store': validated_data.get("feature_multi_store", False),
            'feature_loans': validated_data.get("feature_loans", False),
            'feature_advanced_analytics': validated_data.get("feature_advanced_analytics", False),
            'feature_api_access': validated_data.get("feature_api_access", False),
            'is_active': False,  # Sera activé après le provisioning
            'provisioning_status': 'pending',
        }
        
        # Ajouter le prix personnalisé si le plan est 'custom'
        if plan == 'custom' and validated_data.get('monthly_price'):
            company_data['monthly_price'] = validated_data['monthly_price']
        
        company = Company.objects.create(**company_data)

        # Domaine associé
        domain = Domain.objects.create(
            domain=f"{subdomain}.{base_domain}",
            tenant=company,
            is_primary=True
        )

        # Préparer les données admin pour la tâche asynchrone
        admin_data = {
            'username': validated_data.get("admin_username"),
            'email': validated_data.get("admin_email"),
            'password': validated_data.get("admin_password"),
            'first_name': validated_data.get("admin_first_name", ''),
            'last_name': validated_data.get("admin_last_name", ''),
        }

        # Lancer le provisioning en arrière-plan (migrations + rôles + admin)
        provision_tenant_async.delay(company.id, admin_data)

        return {
            "company": company,
            "domain": domain,
            "provisioning_status": "pending"
        }


class CompanyDetailSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour la gestion superadmin des tenants.
    """
    users_count = serializers.SerializerMethodField()
    stores_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    usage_stats = serializers.SerializerMethodField()
    billing_status = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = '__all__'
    
    def get_plan_name(self, obj):
        """Retourne le nom lisible du plan."""
        plan_names = {
            'starter': 'Starter',
            'business': 'Business',
            'enterprise': 'Enterprise',
            'custom': 'Personnalisé'
        }
        return plan_names.get(obj.plan, 'Standard')
    
    def get_users_count(self, obj):
        """Compte dynamiquement les utilisateurs dans le tenant."""
        from django_tenants.utils import schema_context
        
        try:
            # Changer vers le schéma du tenant et compter les users
            with schema_context(obj.schema_name):
                count = User.objects.count()
                # Mettre à jour le cache pour éviter de compter à chaque fois
                if count != obj.total_users_count:
                    Company.objects.filter(id=obj.id).update(total_users_count=count)
                return count
        except Exception as e:
            # En cas d'erreur, retourner la valeur en cache
            return obj.total_users_count or 0
    
    def get_stores_count(self, obj):
        """Compte dynamiquement les points de vente dans le tenant."""
        from django_tenants.utils import schema_context
        
        try:
            # Changer vers le schéma du tenant et compter les stores
            with schema_context(obj.schema_name):
                from apps.inventory.models import Store
                count = Store.objects.count()
                return count
        except Exception as e:
            # En cas d'erreur (modèle n'existe pas encore ou autre), retourner 0
            return 0
    
    def get_products_count(self, obj):
        """Compte dynamiquement les produits dans le tenant."""
        from django_tenants.utils import schema_context
        
        try:
            # Changer vers le schéma du tenant et compter les produits
            with schema_context(obj.schema_name):
                from apps.inventory.models import Product
                count = Product.objects.count()
                # Mettre à jour le cache
                if count != obj.total_products_count:
                    Company.objects.filter(id=obj.id).update(total_products_count=count)
                return count
        except Exception as e:
            # En cas d'erreur, retourner la valeur en cache
            return obj.total_products_count or 0
    
    def get_last_login(self, obj):
        return obj.last_activity_date
    
    def get_usage_stats(self, obj):
        """Calcule les statistiques d'utilisation avec les vraies données."""
        users_count = self.get_users_count(obj)
        products_count = self.get_products_count(obj)
        
        return {
            'users': {
                'current': users_count,
                'max': obj.max_users,
                'percentage': obj.get_usage_percentage('users')
            },
            'storage': {
                'current_mb': obj.storage_used_mb,
                'max_mb': obj.max_storage_mb,
                'percentage': obj.get_usage_percentage('storage')
            },
            'products': {
                'current': products_count,
                'max': obj.max_products,
                'percentage': (products_count / obj.max_products * 100) if obj.max_products > 0 else 0
            }
        }
    
    def get_billing_status(self, obj):
        latest_billing = obj.billings.filter(status='pending').first()
        return {
            'subscription_expires': obj.subscription_end_date,
            'days_until_expiration': obj.days_until_expiration(),
            'monthly_price': obj.monthly_price,
            'pending_invoice': latest_billing.invoice_number if latest_billing else None,
            'is_trial': obj.trial_end_date and not obj.subscription_end_date,
            'is_expired': obj.is_subscription_expired()
        }


class CompanyUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour mettre à jour les paramètres d'un tenant.
    """
    class Meta:
        model = Company
        fields = [
            'name', 'email', 'phone', 'address',
            'plan', 'max_users', 'max_stores', 'max_products', 'max_storage_mb',
            'feature_services', 'feature_multi_store', 'feature_loans', 
            'feature_advanced_analytics', 'feature_api_access',
            'is_active', 'is_suspended', 'suspension_reason',
            'subscription_end_date', 'monthly_price', 'billing_email'
        ]
    
    def update(self, instance, validated_data):
        # Log the update action
        old_values = {field: getattr(instance, field) for field in validated_data.keys()}
        updated_instance = super().update(instance, validated_data)
        
        # Create audit log
        AuditLog.objects.create(
            company=instance,
            admin_user=self.context['request'].user.username if 'request' in self.context else 'system',
            action_type='company_update',
            action_description=f'Updated company {instance.name}',
            resource_type='company',
            resource_id=str(instance.id),
            old_values=old_values,
            new_values=validated_data
        )
        
        return updated_instance


class CompanyBillingSerializer(serializers.ModelSerializer):
    """
    Serializer pour la gestion des factures.
    """
    company_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = CompanyBilling
        fields = '__all__'
    
    def get_company_name(self, obj):
        """Retourne le nom de l'entreprise de manière sûre."""
        return obj.company.name if obj.company else 'N/A'
    
    def get_is_overdue(self, obj):
        """Retourne si la facture est en retard."""
        return obj.is_overdue()


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer pour les logs d'audit.
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'


class SupportTicketSerializer(serializers.ModelSerializer):
    """
    Serializer pour les tickets de support.
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = '__all__'
        read_only_fields = ('ticket_number', 'created_at', 'updated_at')


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour mettre à jour un ticket de support.
    """
    class Meta:
        model = SupportTicket
        fields = ['status', 'priority', 'assigned_to']
    
    def update(self, instance, validated_data):
        if 'status' in validated_data and validated_data['status'] == 'resolved':
            validated_data['resolved_at'] = timezone.now()
        
        return super().update(instance, validated_data)


class SystemMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les métriques système.
    """
    class Meta:
        model = SystemMetrics
        fields = '__all__'
        read_only_fields = ('recorded_at',)


class SuperAdminDashboardSerializer(serializers.Serializer):
    """
    Serializer pour le dashboard superadmin avec toutes les statistiques.
    """
    # Statistiques générales
    total_companies = serializers.IntegerField()
    active_companies = serializers.IntegerField()
    suspended_companies = serializers.IntegerField()
    trial_companies = serializers.IntegerField()
    
    # Revenus
    monthly_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    yearly_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Alertes
    expiring_soon = serializers.ListField(child=serializers.DictField())
    overdue_payments = serializers.ListField(child=serializers.DictField())
    quota_warnings = serializers.ListField(child=serializers.DictField())
    
    # Métriques techniques
    total_users = serializers.IntegerField()
    total_storage_gb = serializers.FloatField()
    avg_response_time = serializers.IntegerField()
    
    # Activité récente
    recent_signups = serializers.ListField(child=serializers.DictField())
    recent_tickets = serializers.ListField(child=serializers.DictField())

