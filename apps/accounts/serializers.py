"""
User serializers for API.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.accounts.models import User, Role, Permission, UserSession, UserActivity
from django.db.models import Sum
from apps.suppliers.models import Supplier, SupplierPayment
import logging

logger = logging.getLogger(__name__)
### auth   
class LoginSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Optimisation: select_related pour charger le rôle en une seule requête
            from apps.accounts.models import User
            from django.db import connection
            
            try:
                # Ne charger assigned_stores que si on n'est pas dans le schéma public
                if connection.schema_name != 'public':
                    user_with_role = User.objects.select_related('role').prefetch_related('assigned_stores').get(email=email, is_active=True)
                else:
                    user_with_role = User.objects.select_related('role').get(email=email, is_active=True)
            except User.DoesNotExist:
                raise serializers.ValidationError({"detail": "Email ou mot de passe incorrect."})
            
            user = authenticate(request=self.context.get('request'), email=email, password=password)

            if not user:
                raise serializers.ValidationError({"detail": "Email ou mot de passe incorrect."})
            
            # Remplacer user par la version optimisée avec role déjà chargé
            user = user_with_role
            
            # Vérifier si l'entreprise est suspendue
            try:
                tenant = connection.tenant
                
                if tenant and hasattr(tenant, 'is_suspended') and tenant.is_suspended:
                    reason = tenant.suspension_reason or "Votre compte a été suspendu."
                    logger.warning(f"Tentative de connexion refusee - Compte suspendu: {tenant.schema_name}")
                    raise serializers.ValidationError({
                        "detail": f"Accès refusé - Compte suspendu. {reason} Contactez l'administrateur pour plus d'informations."
                    })
            except AttributeError:
                # Pas de tenant (schéma public)
                pass

        else:
            raise serializers.ValidationError('Email et mot de passe sont requis.')

        data = super().validate(attrs)

        # Sérialiser le rôle si présent
        role_data = None
        if user.role:
            role_data = {
                'id': user.role.id,
                'name': user.role.name,
                'display_name': user.role.display_name,
                'can_manage_users': user.role.can_manage_users,
                'can_manage_products': user.role.can_manage_products,
                'can_view_products': user.role.can_view_products,
                'can_manage_categories': user.role.can_manage_categories,
                'can_view_categories': user.role.can_view_categories,
                'can_manage_services': user.role.can_manage_services,
                'can_view_services': user.role.can_view_services,
                'can_manage_inventory': user.role.can_manage_inventory,
                'can_view_inventory': user.role.can_view_inventory,
                'can_manage_sales': user.role.can_manage_sales,
                'can_manage_customers': user.role.can_manage_customers,
                'can_manage_suppliers': user.role.can_manage_suppliers,
                'can_manage_cashbox': user.role.can_manage_cashbox,
                'can_manage_loans': user.role.can_manage_loans,
                'can_manage_expenses': user.role.can_manage_expenses,
                'can_view_analytics': user.role.can_view_analytics,
                'can_export_data': user.role.can_export_data,
            }

        # Récupérer les informations de magasin
        default_store = user.get_default_store()
        default_store_data = None
        if default_store:
            default_store_data = {
                'id': default_store.id,
                'name': default_store.name,
                'code': default_store.code,
            }

        # Récupérer le nom du tenant (company)
        from django.db import connection
        tenant_name = connection.tenant.name if hasattr(connection, 'tenant') else None

        # Construire le nom complet
        full_name = f"{user.first_name} {user.last_name}".strip() if user.first_name or user.last_name else user.username

        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'name': full_name,
            'tenant_name': tenant_name,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'role': role_data,
            'role_name': user.role.display_name if user.role else None,
            'default_store': default_store_data,
            'has_assigned_stores': user.has_assigned_stores(),
            'is_store_restricted': user.is_store_restricted(),
        }
        return data
### end auth

class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""
    
    permissions_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'display_name', 'description', 'access_scope',
            'can_manage_users', 
            'can_manage_products', 'can_view_products',
            'can_manage_categories', 'can_view_categories',
            'can_manage_services', 'can_view_services',
            'can_manage_inventory', 'can_view_inventory',
            'can_manage_sales', 'can_manage_customers',
            'can_manage_suppliers', 'can_manage_cashbox', 'can_manage_bank',
            'can_manage_mobile_money', 'can_manage_loans', 'can_manage_expenses', 
            'can_view_analytics', 'can_export_data', 'permissions_count', 'users_count', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'permissions_count', 'users_count']
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()
    
    def get_users_count(self, obj):
        return obj.users.count()


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model."""
    
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = Permission
        fields = [
            'id', 'name', 'codename', 'description',
            'module', 'module_display', 'action', 'action_display',
            'roles', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list view (minimal data)."""
    
    role_name = serializers.CharField(source='role.display_name', read_only=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    assigned_stores_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'display_name', 'phone', 'avatar', 'employee_id',
            'role', 'role_name', 'assigned_stores_count',
            'is_active', 'is_staff', 'is_superuser', 'last_login', 'date_joined'
        ]
    
    def get_assigned_stores_count(self, obj):
        """Retourne le nombre de stores assignés (0 si schéma public)."""
        from django.db import connection
        
        if connection.schema_name == 'public':
            return 0
        
        try:
            return obj.assigned_stores.count()
        except:
            return 0


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for user detail view (complete data)."""
    
    role_name = serializers.CharField(source='role.display_name', read_only=True)
    secondary_roles_list = RoleSerializer(source='secondary_roles', many=True, read_only=True)
    assigned_stores_list = serializers.SerializerMethodField()
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    default_store = serializers.SerializerMethodField()
    has_assigned_stores = serializers.SerializerMethodField()
    is_store_restricted = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'display_name',
            'phone', 'alternative_phone',
            'avatar', 'address', 'city', 'postal_code', 'country',
            
            # Employee
            'employee_id', 'role', 'role_name',
            'secondary_roles', 'secondary_roles_list', 'assigned_stores',
            'assigned_stores_list', 'default_store', 'has_assigned_stores', 
            'is_store_restricted', 'hire_date', 'termination_date',
            
            # Contact d'urgence
            'emergency_contact_name', 'emergency_contact_phone',
            
            # Status
            'is_active', 'is_staff', 'notes',
            'date_joined', 'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']
    
    def get_assigned_stores_list(self, obj):
        from django.db import connection
        
        # Ne charger les stores que si on est dans un schéma tenant
        if connection.schema_name == 'public':
            return []
        
        from apps.inventory.serializers import StoreMinimalSerializer
        return StoreMinimalSerializer(obj.assigned_stores.all(), many=True).data
    
    def get_default_store(self, obj):
        """Return default store ID for store-restricted users."""
        from django.db import connection
        
        # Ne charger les stores que si on est dans un schéma tenant
        if connection.schema_name == 'public':
            return None
        
        default_store = obj.get_default_store()
        if default_store:
            from apps.inventory.serializers import StoreMinimalSerializer
            return StoreMinimalSerializer(default_store).data
        return None
    
    def get_has_assigned_stores(self, obj):
        """Check if user has assigned stores."""
        from django.db import connection
        
        if connection.schema_name == 'public':
            return False
        
        return obj.has_assigned_stores()
    
    def get_is_store_restricted(self, obj):
        """Check if user is store restricted."""
        from django.db import connection
        
        if connection.schema_name == 'public':
            return False
        
        return obj.is_store_restricted()

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user creation."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone',
            'alternative_phone', 'address', 'city', 'postal_code', 'country',
            
            # Employee
            'employee_id', 'role', 'secondary_roles',
            'assigned_stores',
            'hire_date',
            
            # Contact d'urgence
            'emergency_contact_name', 'emergency_contact_phone',
            
            'notes'
        ]
    
    def validate(self, attrs):
        """Validate user data."""
        # Vérifier que les mots de passe correspondent
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Les mots de passe ne correspondent pas.'
            })
        
        # Le rôle est obligatoire pour les utilisateurs
        if not attrs.get('role'):
            raise serializers.ValidationError({
                'role': 'Le rôle est obligatoire.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create user with password hashing."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        secondary_roles = validated_data.pop('secondary_roles', [])
        assigned_stores = validated_data.pop('assigned_stores', [])
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Ajouter les rôles secondaires
        if secondary_roles:
            user.secondary_roles.set(secondary_roles)
        
        # Assigner les magasins
        if assigned_stores:
            user.assigned_stores.set(assigned_stores)
        
        # Assigner les magasins - COMMENTÉ temporairement
        # if assigned_stores:
        #     user.assigned_stores.set(assigned_stores)
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for user update."""
    
    employee_id = serializers.CharField(read_only=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'alternative_phone',
            'address', 'city', 'postal_code', 'country', 'avatar',
            
            # Employee
            'employee_id', 'role', 'secondary_roles', 'assigned_stores',
            'hire_date', 'termination_date',
            
            # Contact d'urgence
            'emergency_contact_name', 'emergency_contact_phone',
            
            'password',
            'is_active', 'notes'
        ]
    
    def validate_password(self, value):
        """Valider le mot de passe uniquement s'il est fourni."""
        if value and value.strip():
            # Valider uniquement si le mot de passe n'est pas vide
            validate_password(value)
            return value
        # Si vide, retourner None pour l'ignorer
        return None
    
    def update(self, instance, validated_data):
        """Update user."""
        from django.db import connection
        
        secondary_roles = validated_data.pop('secondary_roles', None)
        assigned_stores = validated_data.pop('assigned_stores', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Mettre à jour le mot de passe seulement s'il est fourni et non None
        if password is not None and password:
            instance.set_password(password)
        
        instance.save()
        
        # Mettre à jour les rôles secondaires
        if secondary_roles is not None:
            instance.secondary_roles.set(secondary_roles)
        
        # Mettre à jour les magasins assignés uniquement si on n'est pas dans le schéma public
        if assigned_stores is not None and connection.schema_name != 'public':
            instance.assigned_stores.set(assigned_stores)
        
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate password change data."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Les mots de passe ne correspondent pas.'
            })
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset (admin only)."""
    
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate password reset data."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Les mots de passe ne correspondent pas.'
            })
        return attrs


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions."""
    
    user_name = serializers.CharField(source='user.get_display_name', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'user_name', 'session_key', 'ip_address',
            'user_agent', 'login_time', 'logout_time', 'is_active',
            'duration', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_duration(self, obj):
        """Calculate session duration."""
        if obj.logout_time:
            delta = obj.logout_time - obj.login_time
            return int(delta.total_seconds())
        return None


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activities."""
    
    user_name = serializers.CharField(source='user.get_display_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'user_name', 'action', 'action_display',
            'module', 'object_type', 'object_id', 'description',
            'ip_address', 'created_at'
        ]
        read_only_fields = ['created_at']


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics."""
    
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    staff_users = serializers.IntegerField()
    new_users_this_month = serializers.IntegerField()
    active_sessions = serializers.IntegerField()