# tenants/serializers.py
from rest_framework import serializers
from .models import Company, Domain

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ('domain', 'is_primary')
        read_only_fields = ('tenant',)

class CompanySerializer(serializers.ModelSerializer):
    domains = DomainSerializer(many=True, read_only=True)
    
    class Meta:
        model = Company
        fields = (
            'id', 'name', 'schema_name', 'created_on', 'plan', 
            'max_users', 'is_active', 'domains'
        )
        read_only_fields = ('schema_name', 'created_on')


class TenantProvisioningSerializer(serializers.Serializer):
    """
    Serializer utilisé pour la création initiale d'un nouveau Tenant (Company + Domain).
    """
    name = serializers.CharField(max_length=100, help_text="Nom de la compagnie/tenant.")
    subdomain = serializers.CharField(max_length=100, help_text="Sous-domaine désiré (ex: maboutique).")
    admin_email = serializers.EmailField(help_text="Email de l'administrateur initial du tenant.")
    admin_password = serializers.CharField(
        write_only=True, 
        help_text="Mot de passe de l'administrateur initial."
    )
    plan = serializers.CharField(max_length=50, default='Starter', help_text="Plan tarifaire initial.")

    def validate_subdomain(self, value):
        # Valider que le sous-domaine n'est pas déjà pris ou n'est pas "public"
        if Domain.objects.filter(domain=f'{value}.{self.context.get("base_domain")}').exists():
            raise serializers.ValidationError("Ce sous-domaine est déjà utilisé.")
        if value.lower() in ['www', 'admin', 'api', 'public']:
             raise serializers.ValidationError("Ce sous-domaine est réservé.")
        return value

    def create(self, validated_data):
        
        tenant_name = validated_data['name']
        schema_name = validated_data['subdomain'].lower()
        plan = validated_data['plan']
        
        company = Company.objects.create(
            name=tenant_name, 
            schema_name=schema_name, 
            plan=plan,
        )
        
        Domain.objects.create(
            domain=validated_data['subdomain'] + '.' + self.context.get('base_domain'),
            tenant=company, 
            is_primary=True
        )

        # Création de l'utilisateur administrateur (À implémenter dans l'app accounts)
        # L'application accounts/models.py doit contenir le modèle User avec la ForeignKey vers Company.
        # Cette logique sera déplacée/appellée depuis l'app accounts pour éviter la dépendance circulaire.
        # create_tenant_admin(
        #     company=company, 
        #     email=validated_data['admin_email'], 
        #     password=validated_data['admin_password']
        # )

        return company