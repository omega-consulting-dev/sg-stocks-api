"""
Serializer pour exposer les informations d'utilisateur avec permissions.
"""

from rest_framework import serializers
from apps.accounts.models import User, Role
from apps.inventory.models import Store


class StoreMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'code', 'city']


class RolePermissionsSerializer(serializers.ModelSerializer):
    """Serializer pour exposer toutes les permissions d'un rôle."""
    
    class Meta:
        model = Role
        fields = [
            'name', 'display_name', 'access_scope',
            'can_manage_users', 'can_manage_products', 'can_view_products',
            'can_manage_categories', 'can_view_categories',
            'can_manage_services', 'can_view_services',
            'can_manage_inventory', 'can_view_inventory',
            'can_manage_sales', 'can_manage_customers', 'can_manage_suppliers',
            'can_manage_cashbox', 'can_manage_loans', 'can_manage_expenses',
            'can_view_analytics', 'can_export_data'
        ]


class UserMeSerializer(serializers.ModelSerializer):
    """
    Serializer pour le endpoint /api/v1/auth/me/
    Retourne toutes les infos nécessaires pour le frontend.
    """
    
    role_details = RolePermissionsSerializer(source='role', read_only=True)
    assigned_stores_details = StoreMinimalSerializer(source='assigned_stores', many=True, read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'avatar', 'employee_id',
            'role', 'role_details',
            'assigned_stores', 'assigned_stores_details',
            'is_superuser', 'is_staff',
            'last_login', 'date_joined'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username
