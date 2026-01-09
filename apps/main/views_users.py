"""
Vues pour la gestion des utilisateurs dans le schéma public (SuperAdmin).
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.models import User
from apps.accounts.serializers import UserListSerializer, UserDetailSerializer


class PublicUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des utilisateurs dans le schéma public.
    Utilisé par l'application SuperAdmin.
    """
    permission_classes = [IsAuthenticated]
    queryset = User.objects.filter(is_staff=True).order_by('-date_joined')
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return UserListSerializer
        return UserDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Créer un nouvel utilisateur staff."""
        data = request.data.copy()
        # Forcer is_staff à True pour les utilisateurs du schéma public
        data['is_staff'] = True
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activer un utilisateur."""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'utilisateur activé'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Désactiver un utilisateur."""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'status': 'utilisateur désactivé'})
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Réinitialiser le mot de passe d'un utilisateur."""
        user = self.get_object()
        new_password = request.data.get('password')
        
        if not new_password:
            return Response(
                {'error': 'Le nouveau mot de passe est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        return Response({'status': 'mot de passe réinitialisé'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtenir les statistiques des utilisateurs."""
        total = User.objects.filter(is_staff=True).count()
        active = User.objects.filter(is_staff=True, is_active=True).count()
        superusers = User.objects.filter(is_superuser=True).count()
        
        return Response({
            'total': total,
            'active': active,
            'inactive': total - active,
            'superusers': superusers
        })
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtenir les informations de l'utilisateur connecté."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
