from rest_framework import serializers
from django.db import transaction
from django.core.management import call_command
from .models import Company, Domain
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
            'plan', 'is_active', 'created_on', 'domains'
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

    @transaction.atomic
    def create(self, validated_data):
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

        # Création du tenant
        company = Company.objects.create(
            schema_name=schema_name,
            name=name,
            email=validated_data.get("email"),
            phone=validated_data.get("phone"),
            address=validated_data.get("address"),
            plan=plan,
            max_users=max_users,
            max_stores=max_stores,
            feature_services=validated_data.get("feature_services", False),
            feature_multi_store=validated_data.get("feature_multi_store", False),
            feature_loans=validated_data.get("feature_loans", False),
            feature_advanced_analytics=validated_data.get("feature_advanced_analytics", False),
            feature_api_access=validated_data.get("feature_api_access", False),
        )

        # Domaine associé
        domain = Domain.objects.create(
            domain=f"{subdomain}.{base_domain}",
            tenant=company,
            is_primary=True
        )

        # Migrations automatiques du schema
        call_command('migrate_schemas', schema_name=schema_name, verbosity=0)

        # Création du rôle Manager dans le schéma du tenant
        from django_tenants.utils import connection
        connection.set_tenant(company)
        manager_role, _ = Role.objects.get_or_create(
            name='manager',
            defaults={
                'display_name': 'Gérant/Directeur',
                'description': 'Accès complet à toutes les fonctionnalités',
                'can_manage_users': True,
                'can_manage_products': True,
                'can_manage_inventory': True,
                'can_manage_sales': True,
                'can_manage_customers': True,
                'can_manage_suppliers': True,
                'can_manage_cashbox': True,
                'can_manage_loans': True,
                'can_manage_expenses': True,
                'can_view_analytics': True,
                'access_scope': 'all',
            }
        )

        # Création de l’utilisateur administrateur
        admin_user = User.objects.create_user(
            username=validated_data.get("admin_username"),
            email=validated_data.get("admin_email"),
            password=validated_data.get("admin_password"),
            first_name=validated_data.get("admin_first_name", ''),
            last_name=validated_data.get("admin_last_name", ''),
            is_staff=True,
            is_superuser=False,
            is_collaborator=True,
            role=manager_role,
        )

        return {
            "company": company,
            "domain": domain,
            "admin_user": admin_user
        }
