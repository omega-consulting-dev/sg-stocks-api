"""
User views/viewsets for API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User, Role, Permission, UserSession, UserActivity
from apps.accounts.serializers import (
    UserListSerializer,
    UserDetailSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    ResetPasswordSerializer,
    RoleSerializer,
    PermissionSerializer,
    UserSessionSerializer,
    UserActivitySerializer,
    UserStatsSerializer,
)
from apps.accounts.serializers_permissions import UserMeSerializer
from apps.accounts.filters import UserFilter
from apps.accounts.permissions import IsAdminOrManager

from apps.accounts.serializers import LoginSerializer
from apps.accounts.models import User


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Liste des utilisateurs",
        description="Récupère la liste de tous les utilisateurs (collaborateurs, clients, fournisseurs).",
        tags=["Utilisateurs"]
    ),
    retrieve=extend_schema(
        summary="Détail d'un utilisateur",
        description="Récupère les détails complets d'un utilisateur.",
        tags=["Utilisateurs"]
    ),
    create=extend_schema(
        summary="Créer un utilisateur",
        description="Crée un nouveau utilisateur (collaborateur, client ou fournisseur).",
        tags=["Utilisateurs"]
    ),
    update=extend_schema(
        summary="Modifier un utilisateur",
        description="Modifie un utilisateur existant.",
        tags=["Utilisateurs"]
    ),
    destroy=extend_schema(
        summary="Désactiver un utilisateur",
        description="Désactive un utilisateur (soft delete).",
        tags=["Utilisateurs"]
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model.
    Gestion de tous les types d'utilisateurs : collaborateurs, clients, fournisseurs.
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    search_fields = [
        'username', 'email', 'first_name', 'last_name',
        'employee_id'
    ]
    ordering_fields = ['date_joined', 'username', 'last_name', 'email']
    ordering = ['date_joined']
    
    def get_queryset(self):
        """Filter queryset based on user permissions and schema."""
        from django.db import connection
        
        # Queryset de base
        queryset = User.objects.select_related('role')
        
        # Ajouter prefetch_related uniquement si on est dans un schéma tenant
        # (pas dans public, car les tables inventory n'existent pas dans public)
        if connection.schema_name != 'public':
            queryset = queryset.prefetch_related('secondary_roles', 'assigned_stores')
        else:
            queryset = queryset.prefetch_related('secondary_roles')
        
        user = self.request.user
        
        # Super admin voit tout
        if user.is_superuser:
            return queryset
        
        # Manager voit tout dans son tenant
        if hasattr(user, 'role') and user.role and user.role.access_scope == 'all':
            return queryset
        
        # Les autres ne voient que les utilisateurs des magasins assignés
        # TEMPORAIRE: assigned_stores commenté, retourne tous les utilisateurs
        # accessible_stores = user.get_accessible_stores()
        # return queryset.filter(
        #     Q(assigned_stores__in=accessible_stores) |
        #     Q(id=user.id)  # Peut toujours voir son propre profil
        # ).distinct()
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        elif self.action == 'reset_password':
            return ResetPasswordSerializer
        return UserDetailSerializer
    
    def destroy(self, request, *args, **kwargs):
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete: mark as inactive instead of deleting."""
        instance = self.get_object()
        instance.is_active = False
        instance.is_active_employee = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def perform_create(self, serializer):
        """Valider la limite d'utilisateurs avant la création."""
        from apps.tenants.models import Company
        from django.db import connection
        
        schema_name = connection.schema_name
        if schema_name != 'public':
            try:
                company = Company.objects.using('default').get(schema_name=schema_name)
                
                # Vérifier si on peut ajouter un utilisateur
                if not company.can_add_user():
                    from rest_framework.exceptions import ValidationError
                    max_u = company.max_users
                    current_count = User.objects.count()
                    next_plan = "Business" if company.plan == "starter" else "Enterprise"
                    
                    raise ValidationError({
                        'detail': f"Limite d'utilisateurs atteinte ({current_count}/{max_u}). Passez au plan {next_plan} pour ajouter plus d'utilisateurs."
                    })
            except Company.DoesNotExist:
                pass
        
        serializer.save()
    
    @extend_schema(
        summary="Profil de l'utilisateur connecté",
        description="Récupère le profil de l'utilisateur actuellement connecté avec toutes les permissions.",
        tags=["Utilisateurs"]
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile with permissions."""
        serializer = UserMeSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Mettre à jour le profil",
        description="Met à jour le profil de l'utilisateur connecté.",
        tags=["Utilisateurs"]
    )
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user profile."""
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Changer le mot de passe",
        description="Change le mot de passe de l'utilisateur connecté.",
        tags=["Utilisateurs"],
        request=ChangePasswordSerializer
    )
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change password for current user."""
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            # Vérifier l'ancien mot de passe
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'old_password': 'Mot de passe incorrect.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Définir le nouveau mot de passe
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({'message': 'Mot de passe changé avec succès.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Réinitialiser le mot de passe",
        description="Réinitialise le mot de passe d'un utilisateur (admin uniquement).",
        tags=["Utilisateurs"],
        request=ResetPasswordSerializer
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def reset_password(self, request, pk=None):
        """Reset password for a user (admin only)."""
        user = self.get_object()
        serializer = ResetPasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({'message': 'Mot de passe réinitialisé avec succès.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Activer un utilisateur",
        description="Active un utilisateur désactivé.",
        tags=["Utilisateurs"]
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def activate(self, request, pk=None):
        """Activate a user."""
        user = self.get_object()
        user.is_active = True
        user.is_active_employee = True if user.is_collaborator else user.is_active_employee
        user.save()
        return Response({'message': 'Utilisateur activé avec succès.'})
    
    @extend_schema(
        summary="Désactiver un utilisateur",
        description="Désactive un utilisateur actif.",
        tags=["Utilisateurs"]
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def deactivate(self, request, pk=None):
        """Deactivate a user."""
        user = self.get_object()
        user.is_active = False
        user.is_active_employee = False
        user.save()
        return Response({'message': 'Utilisateur désactivé avec succès.'})
    
    @extend_schema(
        summary="Collaborateurs uniquement",
        description="Récupère la liste des collaborateurs uniquement.",
        tags=["Utilisateurs"]
    )
    @action(detail=False, methods=['get'])
    def collaborators(self, request):
        """Get only collaborators."""
        queryset = self.filter_queryset(
            self.get_queryset().filter(is_collaborator=True)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Statistiques des utilisateurs",
        description="Récupère les statistiques globales des utilisateurs.",
        tags=["Utilisateurs"]
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics."""
        one_month_ago = timezone.now() - timedelta(days=30)
        
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'new_users_this_month': User.objects.filter(
                date_joined__gte=one_month_ago
            ).count(),
            'active_sessions': UserSession.objects.filter(is_active=True).count(),
        }
        
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Activités de l'utilisateur",
        description="Récupère l'historique des activités d'un utilisateur.",
        tags=["Utilisateurs"]
    )
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Get user activities."""
        user = self.get_object()
        activities = UserActivity.objects.filter(user=user).order_by('created_at')[:50]
        serializer = UserActivitySerializer(activities, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Sessions de l'utilisateur",
        description="Récupère l'historique des sessions d'un utilisateur.",
        tags=["Utilisateurs"]
    )
    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get user sessions."""
        user = self.get_object()
        sessions = UserSession.objects.filter(user=user).order_by('login_time')[:20]
        serializer = UserSessionSerializer(sessions, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Liste des rôles",
        description="Récupère la liste de tous les rôles.",
        tags=["Rôles"]
    ),
)
class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Role model.
    """
    
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'display_name', 'description']
    ordering_fields = ['name', 'display_name', 'created_at']
    ordering = ['display_name']
    
    @extend_schema(
        summary="Choix de rôles disponibles",
        description="Récupère la liste des choix de rôles prédéfinis.",
        tags=["Rôles"]
    )
    @action(detail=False, methods=['get'])
    def choices(self, request):
        """Get available role choices."""
        choices = [
            {'value': choice[0], 'label': choice[1]}
            for choice in Role.ROLE_CHOICES
        ]
        return Response(choices)
    
    @extend_schema(
        summary="Utilisateurs d'un rôle",
        description="Récupère la liste des utilisateurs ayant ce rôle.",
        tags=["Rôles"]
    )
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Get users with this role."""
        role = self.get_object()
        users = User.objects.filter(
            Q(role=role) | Q(secondary_roles=role)
        ).distinct()
        serializer = UserListSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Liste des permissions",
        description="Récupère la liste de toutes les permissions.",
        tags=["Permissions"]
    ),
)
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Permission model (read-only).
    """
    
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['module', 'action']
    search_fields = ['name', 'codename', 'description']
    ordering = ['module', 'action']


@extend_schema_view(
    list=extend_schema(
        summary="Sessions actives",
        description="Récupère la liste de toutes les sessions actives.",
        tags=["Sessions"]
    ),
)
class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for UserSession model (read-only).
    """
    
    queryset = UserSession.objects.select_related('user').order_by('login_time')
    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'is_active']
    search_fields = ['user__username', 'ip_address']
    ordering_fields = ['login_time', 'logout_time']
    ordering = ['login_time']
    
    @extend_schema(
        summary="Terminer une session",
        description="Termine une session active.",
        tags=["Sessions"]
    )
    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """Terminate a session."""
        session = self.get_object()
        session.is_active = False
        session.logout_time = timezone.now()
        session.save()
        return Response({'message': 'Session terminée avec succès.'})


@extend_schema_view(
    list=extend_schema(
        summary="Historique des activités",
        description="Récupère l'historique de toutes les activités.",
        tags=["Activités"]
    ),
)
class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for UserActivity model (read-only).
    """
    
    queryset = UserActivity.objects.select_related('user').order_by('created_at')
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'action', 'module']
    search_fields = ['user__username', 'description', 'module']
    ordering_fields = ['created_at', 'action']
    ordering = ['created_at']

