"""
User serializers for API.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.accounts.models import User, Role, Permission, UserSession, UserActivity


### auth   
class LoginSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)

            if not user:
                raise serializers.ValidationError({"login_error": "Email ou mot de passe incorrect."})

        else:
            raise serializers.ValidationError('Email et mot de passe sont requis.')

        data = super().validate(attrs)

        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
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
            'can_manage_users', 'can_manage_products', 'can_manage_services',
            'can_manage_inventory', 'can_manage_sales', 'can_manage_customers',
            'can_manage_suppliers', 'can_manage_cashbox', 'can_manage_loans',
            'can_manage_expenses', 'can_view_analytics', 'can_export_data',
            'permissions_count', 'users_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
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
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'display_name', 'user_type', 'user_type_display',
            'phone', 'avatar', 'role_name',
            'is_collaborator', 'is_customer', 'is_supplier',
            'is_active', 'is_active_employee', 'date_joined'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for user detail view (complete data)."""
    
    role_name = serializers.CharField(source='role.display_name', read_only=True)
    secondary_roles_list = RoleSerializer(source='secondary_roles', many=True, read_only=True)
    assigned_stores_list = serializers.SerializerMethodField()
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    customer_balance = serializers.SerializerMethodField()
    supplier_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'display_name',
            'user_type', 'user_type_display', 'phone', 'alternative_phone',
            'avatar', 'address', 'city', 'postal_code', 'country',
            
            # Collaborateur
            'is_collaborator', 'employee_id', 'role', 'role_name',
            'secondary_roles', 'secondary_roles_list', 'assigned_stores',
            'assigned_stores_list', 'hire_date', 'termination_date',
            'is_active_employee',
            
            # Client
            'is_customer', 'customer_code', 'customer_company_name',
            'customer_tax_id', 'customer_credit_limit', 'customer_payment_term',
            'customer_balance',
            
            # Fournisseur
            'is_supplier', 'supplier_code', 'supplier_company_name',
            'supplier_tax_id', 'supplier_bank_account', 'supplier_rating',
            'supplier_balance',
            
            # Contact d'urgence
            'emergency_contact_name', 'emergency_contact_phone',
            
            # Status
            'is_active', 'is_staff', 'notes',
            'date_joined', 'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']
    
    def get_assigned_stores_list(self, obj):
        from apps.inventory.serializers import StoreMinimalSerializer
        return StoreMinimalSerializer(obj.assigned_stores.all(), many=True).data
    
    def get_customer_balance(self, obj):
        if obj.is_customer:
            return float(obj.get_customer_balance())
        return None
    
    def get_supplier_balance(self, obj):
        if obj.is_supplier:
            return float(obj.get_supplier_balance())
        return None


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
            'first_name', 'last_name', 'user_type', 'phone',
            'alternative_phone', 'address', 'city', 'postal_code', 'country',
            
            # Collaborateur
            'is_collaborator', 'employee_id', 'role', 'secondary_roles',
            'assigned_stores', 'hire_date',
            
            # Client
            'is_customer', 'customer_code', 'customer_company_name',
            'customer_tax_id', 'customer_credit_limit', 'customer_payment_term',
            
            # Fournisseur
            'is_supplier', 'supplier_code', 'supplier_company_name',
            'supplier_tax_id', 'supplier_bank_account', 'supplier_rating',
            
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
        
        # Vérifier qu'au moins un type d'utilisateur est défini
        if not any([attrs.get('is_collaborator'), attrs.get('is_customer'), attrs.get('is_supplier')]):
            raise serializers.ValidationError({
                'user_type': 'L\'utilisateur doit être au moins un collaborateur, un client ou un fournisseur.'
            })
        
        # Si collaborateur, le rôle est obligatoire
        if attrs.get('is_collaborator') and not attrs.get('role'):
            raise serializers.ValidationError({
                'role': 'Le rôle est obligatoire pour un collaborateur.'
            })
        
        # Si client, le code client est obligatoire
        if attrs.get('is_customer') and not attrs.get('customer_code'):
            raise serializers.ValidationError({
                'customer_code': 'Le code client est obligatoire.'
            })
        
        # Si fournisseur, le code fournisseur est obligatoire
        if attrs.get('is_supplier') and not attrs.get('supplier_code'):
            raise serializers.ValidationError({
                'supplier_code': 'Le code fournisseur est obligatoire.'
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
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for user update."""
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'alternative_phone',
            'address', 'city', 'postal_code', 'country', 'avatar',
            
            # Collaborateur
            'employee_id', 'role', 'secondary_roles', 'assigned_stores',
            'hire_date', 'termination_date', 'is_active_employee',
            
            # Client
            'customer_company_name', 'customer_tax_id',
            'customer_credit_limit', 'customer_payment_term',
            
            # Fournisseur
            'supplier_company_name', 'supplier_tax_id',
            'supplier_bank_account', 'supplier_rating',
            
            # Contact d'urgence
            'emergency_contact_name', 'emergency_contact_phone',
            
            'is_active', 'notes'
        ]
    
    def update(self, instance, validated_data):
        """Update user."""
        secondary_roles = validated_data.pop('secondary_roles', None)
        assigned_stores = validated_data.pop('assigned_stores', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Mettre à jour les rôles secondaires
        if secondary_roles is not None:
            instance.secondary_roles.set(secondary_roles)
        
        # Mettre à jour les magasins assignés
        if assigned_stores is not None:
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
    collaborators = serializers.IntegerField()
    customers = serializers.IntegerField()
    suppliers = serializers.IntegerField()
    new_users_this_month = serializers.IntegerField()
    active_sessions = serializers.IntegerField()