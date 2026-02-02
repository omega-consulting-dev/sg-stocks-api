"""
Vues pour la gestion des utilisateurs dans le schéma public (SuperAdmin).
"""
from rest_framework import viewsets, status
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.password_validation import validate_password
from apps.main.models import User  # Utiliser le modèle User du schéma public
from apps.accounts.serializers import UserListSerializer, UserDetailSerializer


class PublicUserCreateSerializer(drf_serializers.ModelSerializer):
    """Serializer pour créer un utilisateur dans le schéma public."""
    
    password = drf_serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = drf_serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone',
            'employee_id', 'role',
            'is_active', 'is_staff', 'is_superuser'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise drf_serializers.ValidationError({
                'password_confirm': 'Les mots de passe ne correspondent pas.'
            })
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PublicUserUpdateSerializer(drf_serializers.ModelSerializer):
    """Serializer pour modifier un utilisateur dans le schéma public."""
    
    password = drf_serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'}
    )
    phone = drf_serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    employee_id = drf_serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    role = drf_serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    # secondary_roles supprimé car non présent dans le modèle User public
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'employee_id', 'role',
            'password', 'is_active', 'is_staff', 'is_superuser'
        ]
    
    def validate_password(self, value):
        if value and value.strip():
            validate_password(value)
            return value
        return None
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # Mettre à jour le mot de passe seulement s'il est fourni et non None
        if password is not None and password:
            instance.set_password(password)
        instance.save()
        return instance


class PublicUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des utilisateurs dans le schéma public.
    Utilisé par l'application SuperAdmin.
    """
    permission_classes = [IsAuthenticated]
    # Afficher tous les utilisateurs sauf les anonymes (username vide)
    queryset = User.objects.exclude(username='').order_by('-date_joined')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'create':
            return PublicUserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PublicUserUpdateSerializer
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
