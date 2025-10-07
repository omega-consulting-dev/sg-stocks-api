from django.db import transaction

from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from rest_framework.response import Response
from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import viewsets
from rest_framework.exceptions import MethodNotAllowed

from apps.users.serializers import RegisterSerializer, LoginSerializer, UserSerializer
from apps.users.models import User
from apps.users.permissions import AdminPermission


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = serializer.data
        data["token"] = serializer.get_token(user)
        return Response(data, status=status.HTTP_201_CREATED)
    

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

