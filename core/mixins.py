"""
Mixins pour filtrer automatiquement les données selon les permissions utilisateur.
"""

from rest_framework.exceptions import PermissionDenied


class StoreAccessMixin:
    """
    Mixin pour filtrer les données selon les stores assignés à l'utilisateur.
    Utiliser ce mixin dans les ViewSets qui ont un champ 'store' ou relation avec Store.
    """
    
    def get_queryset(self):
        """
        Filtrer automatiquement les données selon les stores de l'utilisateur.
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Super admin voit tout
        if user.is_superuser:
            return queryset
        
        # Vérifier si l'utilisateur a un rôle
        if not hasattr(user, 'role') or not user.role:
            return queryset.none()
        
        # Si le rôle a accès à tous les stores
        if user.role.access_scope == 'all':
            return queryset
        
        # Si le rôle a accès uniquement aux stores assignés
        if user.role.access_scope == 'assigned':
            # Déterminer le champ du store dans le queryset
            store_field = self.get_store_field_name()
            
            if store_field:
                filter_kwargs = {f'{store_field}__in': user.assigned_stores.all()}
                return queryset.filter(**filter_kwargs)
        
        # Si le rôle a accès uniquement à ses propres données
        if user.role.access_scope == 'own':
            return queryset.filter(created_by=user)
        
        return queryset
    
    def get_store_field_name(self):
        """
        Déterminer le nom du champ store dans le modèle.
        Override cette méthode si le champ a un nom différent.
        """
        model = self.queryset.model
        
        # Vérifier les champs possibles
        for field_name in ['store', 'source_store', 'destination_store']:
            if hasattr(model, field_name):
                return field_name
        
        return None


class PermissionCheckMixin:
    """
    Mixin pour vérifier les permissions basées sur le rôle de l'utilisateur.
    """
    
    # Définir le nom de la permission requise pour chaque action
    permission_map = {
        'list': None,
        'retrieve': None,
        'create': 'can_manage',
        'update': 'can_manage',
        'partial_update': 'can_manage',
        'destroy': 'can_manage',
    }
    
    # Nom du module (ex: 'products', 'inventory', 'sales')
    module_name = None
    
    def check_permissions(self, request):
        """
        Vérifier les permissions avant d'exécuter l'action.
        """
        super().check_permissions(request)
        
        user = request.user
        action = self.action
        
        # Super admin a tous les droits
        if user.is_superuser:
            return
        
        # Vérifier si l'utilisateur a un rôle
        if not hasattr(user, 'role') or not user.role:
            raise PermissionDenied("Vous n'avez pas de rôle assigné.")
        
        # Déterminer la permission requise
        permission_needed = self.permission_map.get(action)
        
        if not permission_needed:
            return  # Pas de permission spécifique requise
        
        # Construire le nom de la permission
        if self.module_name:
            permission_attr = f'{permission_needed}_{self.module_name}'
        else:
            permission_attr = permission_needed
        
        # Vérifier si le rôle a la permission
        if not getattr(user.role, permission_attr, False):
            raise PermissionDenied(
                f"Votre rôle '{user.role.display_name}' n'a pas la permission de {action} dans ce module."
            )


class UserStoreValidationMixin:
    """
    Mixin pour valider que l'utilisateur a accès au store lors de la création/modification.
    """
    
    def perform_create(self, serializer):
        """
        Valider que l'utilisateur a accès au store avant de créer.
        """
        user = self.request.user
        
        # Récupérer le store depuis les données validées
        store = serializer.validated_data.get('store')
        
        if store and not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if user.role.access_scope == 'assigned':
                    if store not in user.assigned_stores.all():
                        raise PermissionDenied(
                            f"Vous n'avez pas accès au magasin '{store.name}'. "
                            f"Contactez votre administrateur."
                        )
        
        serializer.save(created_by=user)
    
    def perform_update(self, serializer):
        """
        Valider que l'utilisateur a accès au store avant de modifier.
        """
        user = self.request.user
        
        # Récupérer le nouveau store si modifié
        store = serializer.validated_data.get('store')
        
        if store and not user.is_superuser:
            if hasattr(user, 'role') and user.role:
                if user.role.access_scope == 'assigned':
                    if store not in user.assigned_stores.all():
                        raise PermissionDenied(
                            f"Vous n'avez pas accès au magasin '{store.name}'. "
                            f"Contactez votre administrateur."
                        )
        
        serializer.save(updated_by=user)


class StoreAssignmentMixin:
    """
    Mixin pour auto-assigner le magasin par défaut pour les utilisateurs restreints.
    Les utilisateurs admin peuvent sélectionner n'importe quel magasin.
    Les utilisateurs restreints (magasinier, caissier) sont automatiquement assignés à leur magasin.
    """
    
    def get_serializer_context(self):
        """
        Ajouter l'information de restriction de magasin au contexte du serializer.
        """
        context = super().get_serializer_context()
        user = self.request.user
        
        context['is_store_restricted'] = user.is_store_restricted() if hasattr(user, 'is_store_restricted') else False
        context['default_store'] = user.get_default_store() if hasattr(user, 'get_default_store') else None
        
        return context
    
    def perform_create(self, serializer):
        """
        Auto-assigner le magasin par défaut pour les utilisateurs restreints lors de la création.
        """
        user = self.request.user
        
        # Vérifier si l'utilisateur est restreint à un magasin
        if hasattr(user, 'is_store_restricted') and user.is_store_restricted():
            # Si le store n'est pas fourni, utiliser le magasin par défaut
            if 'store' not in serializer.validated_data or serializer.validated_data.get('store') is None:
                default_store = user.get_default_store()
                if default_store:
                    serializer.validated_data['store'] = default_store
                else:
                    raise PermissionDenied(
                        "Vous devez être assigné à un magasin pour effectuer cette action. "
                        "Contactez votre administrateur."
                    )
            else:
                # Si un store est fourni, valider que l'utilisateur y a accès
                provided_store = serializer.validated_data.get('store')
                if provided_store not in user.assigned_stores.all():
                    raise PermissionDenied(
                        f"Vous n'avez pas accès au magasin '{provided_store.name}'. "
                        f"Contactez votre administrateur."
                    )
        
        # Appeler le parent s'il existe
        if hasattr(super(), 'perform_create'):
            super().perform_create(serializer)
        else:
            serializer.save(created_by=user)
    
    def perform_update(self, serializer):
        """
        Valider l'accès au magasin pour les utilisateurs restreints lors de la modification.
        """
        user = self.request.user
        
        # Vérifier si l'utilisateur est restreint à un magasin
        if hasattr(user, 'is_store_restricted') and user.is_store_restricted():
            # Si un nouveau store est fourni, valider l'accès
            if 'store' in serializer.validated_data:
                new_store = serializer.validated_data.get('store')
                if new_store and new_store not in user.assigned_stores.all():
                    raise PermissionDenied(
                        f"Vous n'avez pas accès au magasin '{new_store.name}'. "
                        f"Contactez votre administrateur."
                    )
        
        # Appeler le parent s'il existe
        if hasattr(super(), 'perform_update'):
            super().perform_update(serializer)
        else:
            serializer.save(updated_by=user)
