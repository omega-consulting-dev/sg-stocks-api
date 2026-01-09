"""
Vues d'authentification pour le Super Admin (schéma public).
"""
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate


class SuperAdminLoginSerializer(TokenObtainPairSerializer):
    """
    Serializer pour l'authentification des super admins.
    Simplifié car les utilisateurs du schéma public n'ont pas de role/store.
    """
    username_field = 'email'

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError('Email et mot de passe sont requis.')

        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password
        )

        if not user:
            raise serializers.ValidationError({
                "login_error": "Email ou mot de passe incorrect."
            })

        # Vérifier que c'est bien un staff/superuser
        if not user.is_staff:
            raise serializers.ValidationError({
                "login_error": "Accès refusé. Réservé aux administrateurs."
            })

        # Appeler la validation parent pour générer les tokens
        data = super().validate(attrs)

        # Ajouter les informations de l'utilisateur
        full_name = f"{user.first_name} {user.last_name}".strip() if user.first_name or user.last_name else user.username

        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'name': full_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        }

        return data


class SuperAdminLoginView(TokenObtainPairView):
    """
    Vue de connexion pour les super administrateurs (schéma public).
    """
    serializer_class = SuperAdminLoginSerializer
