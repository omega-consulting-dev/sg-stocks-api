from rest_framework import viewsets
from apps.accounts.models import User
from apps.accounts.serializers import UserListSerializer, UserDetailSerializer

class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for customers (read-only).
    Uses User model with is_customer=True
    """
    permission_classes = []
    
    def get_queryset(self):
        return User.objects.filter(is_customer=True)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer