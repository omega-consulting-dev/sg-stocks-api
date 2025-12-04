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
    
    # Type filters
    user_type = django_filters.ChoiceFilter(choices=User.USER_TYPE_CHOICES)
    is_collaborator = django_filters.BooleanFilter()
    is_customer = django_filters.BooleanFilter()
    is_supplier = django_filters.BooleanFilter()
    
    # Status filters
    is_active = django_filters.BooleanFilter()
    is_active_employee = django_filters.BooleanFilter()
    is_staff = django_filters.BooleanFilter()
    
    # Role filter
    role = django_filters.NumberFilter(field_name='role__id')
    role_name = django_filters.CharFilter(field_name='role__name')
    
    # Store filter
    assigned_store = django_filters.NumberFilter(field_name='assigned_stores__id')
    
    # Customer filters
    customer_code = django_filters.CharFilter(lookup_expr='icontains')
    customer_company_name = django_filters.CharFilter(lookup_expr='icontains')
    
    # Supplier filters
    supplier_code = django_filters.CharFilter(lookup_expr='icontains')
    supplier_company_name = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = User
        fields = {
            'username': ['exact', 'icontains'],
            'email': ['exact', 'icontains'],
            'first_name': ['exact', 'icontains'],
            'last_name': ['exact', 'icontains'],
            'user_type': ['exact'],
            'is_collaborator': ['exact'],
            'is_customer': ['exact'],
            'is_supplier': ['exact'],
            'is_active': ['exact'],
            'is_active_employee': ['exact'],
            'is_staff': ['exact'],
            'role': ['exact'],
            'assigned_stores': ['exact'],
            'customer_code': ['exact', 'icontains'],
            'customer_company_name': ['exact', 'icontains'],
            'supplier_code': ['exact', 'icontains'],
            'supplier_company_name': ['exact', 'icontains'],
            'date_joined': ['gte', 'lte'],
            'hire_date': ['gte', 'lte'],
        }