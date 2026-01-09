"""
User filters for API.
"""

import django_filters
from apps.accounts.models import User


class UserFilter(django_filters.FilterSet):
    """Filter set for User model."""
    
    username = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    
    # Status filters
    is_active = django_filters.BooleanFilter()
    is_staff = django_filters.BooleanFilter()
    
    # Role filter
    role = django_filters.NumberFilter(field_name='role__id')
    role_name = django_filters.CharFilter(field_name='role__name')
    
    # Store filter - COMMENTÉ car assigned_stores est temporairement désactivé
    # assigned_store = django_filters.NumberFilter(field_name='assigned_stores__id')
    
    # Employee filter
    employee_id = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = User
        fields = {
            'username': ['exact', 'icontains'],
            'email': ['exact', 'icontains'],
            'first_name': ['exact', 'icontains'],
            'last_name': ['exact', 'icontains'],
            'is_active': ['exact'],
            'is_staff': ['exact'],
            'role': ['exact'],
            # 'assigned_stores': ['exact'],  # COMMENTÉ car champ temporairement désactivé
            'employee_id': ['exact', 'icontains'],
            'date_joined': ['gte', 'lte'],
            'hire_date': ['gte', 'lte'],
        }