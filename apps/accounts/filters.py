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
    
    # Date filters
    date_joined_after = django_filters.DateFilter(field_name='date_joined', lookup_expr='gte')
    date_joined_before = django_filters.DateFilter(field_name='date_joined', lookup_expr='lte')
    hire_date_after = django_filters.DateFilter(field_name='hire_date', lookup_expr='gte')
    hire_date_before = django_filters.DateFilter(field_name='hire_date', lookup_expr='lte')
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'user_type', 'is_collaborator', 'is_customer', 'is_supplier',
            'is_active', 'is_active_employee', 'is_staff',
            'role', 'role_name', 'assigned_store',
            'customer_code', 'customer_company_name',
            'supplier_code', 'supplier_company_name',
            'date_joined_after', 'date_joined_before',
            'hire_date_after', 'hire_date_before'
        ]