"""
Custom permissions for accounts app.
"""

from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


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
        if hasattr(request.user, 'role') and request.user.role:
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
        if hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['manager', 'super_admin']:
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
        if hasattr(request.user, 'role') and request.user.role and request.user.role.can_manage_users:
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
        if hasattr(request.user, 'role') and request.user.role and request.user.role.access_scope == 'all':
            return True
        
        return True  # La vérification détaillée se fait au niveau de l'objet
    
    def has_object_permission(self, request, view, obj):
        # Super admin a tous les droits
        if request.user.is_superuser:
            return True
        
        # Manager a accès à tous les magasins
        if hasattr(request.user, 'role') and request.user.role and request.user.role.access_scope == 'all':
            return True
        
        # Vérifier si l'utilisateur a accès au magasin
        if hasattr(request.user, 'can_access_store'):
            return request.user.can_access_store(obj)
        
        return False


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

        # Mapper les actions REST aux formes lisibles
        action_map = {
            'list': 'view',
            'retrieve': 'view',
            'create': 'add',
            'update': 'change',
            'partial_update': 'change',
            'destroy': 'delete',
        }

        # Déterminer l'action courante normalisée
        action = action_map.get(getattr(view, 'action', None), getattr(view, 'action', None))

        # Résolution de la permission à vérifier (priorité):
        # 1) view.permission_name (si défini explicitement sur la vue)
        # 2) view.action_required (str ou dict) — si dict, on prend la valeur pour l'action courante
        # 3) tentative de permission granulaires: 'can_{action}_{module}' (ex: can_add_products)
        # 4) fallback générique: 'can_manage_{module}' (ex: can_manage_products)

        permission_name = getattr(view, 'permission_name', None)

        if not permission_name and action_required:
            # action_required peut être une string (nom direct) ou un dict mapping action->perm
            if isinstance(action_required, dict):
                permission_name = action_required.get(getattr(view, 'action', None)) or action_required.get(action)
            else:
                # string: utiliser telle quelle
                permission_name = action_required

        if not permission_name and module_name and action:
            # exemple: can_add_products, can_view_products, can_change_products, etc.
            permission_name = f'can_{action}_{module_name}'

        if not permission_name and module_name:
            # dernier recours: drapeau général du module
            permission_name = f'can_manage_{module_name}'

        if not permission_name:
            logger.info("HasModulePermission denied: no permission_name resolved (user=%s, action=%s, module=%s)",
                        getattr(request.user, 'id', None), getattr(view, 'action', None), module_name)
            return False

        # Vérifier la permission via le rôle (méthode existante sur User)
        if hasattr(request.user, 'has_permission'):
            allowed = request.user.has_permission(permission_name)
            if not allowed:
                # Log useful context for debugging why permission was denied
                logger.info(
                    "HasModulePermission denied: user=%s is_superuser=%s role=%s permission_checked=%s action=%s view=%s",
                    getattr(request.user, 'id', None),
                    getattr(request.user, 'is_superuser', False),
                    getattr(getattr(request.user, 'role', None), 'name', None),
                    permission_name,
                    getattr(view, 'action', None),
                    view.__class__.__name__,
                )
            return allowed

        return False
