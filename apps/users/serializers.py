from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.users.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email']

class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirmation = serializers.CharField(write_only=True, required=True)
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirmation', 'token']
        read_only_fields = ['token']

    def get_token(self, user):
        token = RefreshToken.for_user(user)
        return {
            "access": str(token.access_token),
            "refresh": str(token),
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError({"password": "La confirmation du mot de passe incorrecte."})
        
        attrs.pop('password_confirmation')
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
    
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
