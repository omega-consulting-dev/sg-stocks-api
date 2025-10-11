"""
Custom permissions for accounts app.
"""

from rest_framework import permissions


class IsAdminOrManager(permissions.BasePermission):
    """
    Permission pour les administrateurs et gérants uniquement.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin a tous les droits
        if request.user.is_superuser:
            return True
        
        # Manager ou role avec can_manage_users
        if request.user.role:
            if request.user.role.name in ['manager', 'super_admin']:
                return True
            if request.user.role.can_manage_users:
                return True
        
        return False


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission pour le propriétaire de l'objet ou un admin.
    """
    
    def has_object_permission(self, request, view, obj):
        # Super admin a tous les droits
        if request.user.is_superuser:
            return True
        
        # L'utilisateur peut accéder à son propre profil
        if obj == request.user:
            return True
        
        # Les managers peuvent accéder à tous les profils
        if request.user.role and request.user.role.name in ['manager', 'super_admin']:
            return True
        
        return False


class CanManageUsers(permissions.BasePermission):
    """
    Permission pour gérer les utilisateurs.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin a tous les droits
        if request.user.is_superuser:
            return True
        
        # Vérifier la permission can_manage_users
        if request.user.role and request.user.role.can_manage_users:
            return True
        
        return False


class CanAccessStore(permissions.BasePermission):
    """
    Permission pour accéder à un point de vente spécifique.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin a tous les droits
        if request.user.is_superuser:
            return True
        
        # Manager a accès à tous les magasins
        if request.user.role and request.user.role.access_scope == 'all':
            return True
        
        return True  # La vérification détaillée se fait au niveau de l'objet
    
    def has_object_permission(self, request, view, obj):
        # Super admin a tous les droits
        if request.user.is_superuser:
            return True
        
        # Manager a accès à tous les magasins
        if request.user.role and request.user.role.access_scope == 'all':
            return True
        
        # Vérifier si l'utilisateur a accès au magasin
        return request.user.can_access_store(obj)


class HasModulePermission(permissions.BasePermission):
    """
    Permission basée sur le module et l'action.
    Usage: Dans le viewset, définir module_name et action_required
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin a tous les droits
        if request.user.is_superuser:
            return True
        
        # Récupérer le module et l'action depuis la vue
        module_name = getattr(view, 'module_name', None)
        action_required = getattr(view, 'action_required', None)
        
        if not module_name or not action_required:
            return False
        
        # Mapper les actions REST aux permissions
        action_map = {
            'list': 'view',
            'retrieve': 'view',
            'create': 'add',
            'update': 'change',
            'partial_update': 'change',
            'destroy': 'delete',
        }
        
        action = action_map.get(view.action, view.action)
        permission_name = f'can_manage_{module_name}'
        
        # Vérifier la permission via le rôle
        return request.user.has_permission(permission_name)
