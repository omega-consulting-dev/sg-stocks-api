"""
Customer filters for API.
"""

import django_filters
from apps.customers.models import Customer


class CustomerFilter(django_filters.FilterSet):
    """Filter set for Customer model."""
    
    # Text search filters
    customer_code = django_filters.CharFilter(lookup_expr='icontains')
    name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    phone = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(lookup_expr='icontains')
    country = django_filters.CharFilter(lookup_expr='icontains')
    
    # Exact match filters
    payment_term = django_filters.ChoiceFilter(choices=Customer.PAYMENT_TERM_CHOICES)
    is_active = django_filters.BooleanFilter()
    
    # Range filters
    credit_limit_min = django_filters.NumberFilter(field_name='credit_limit', lookup_expr='gte')
    credit_limit_max = django_filters.NumberFilter(field_name='credit_limit', lookup_expr='lte')
    
    # Date filters
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Customer
        fields = {
            'customer_code': ['exact', 'icontains'],
            'name': ['exact', 'icontains'],
            'email': ['exact', 'icontains'],
            'phone': ['exact', 'icontains'],
            'city': ['exact', 'icontains'],
            'country': ['exact', 'icontains'],
            'payment_term': ['exact'],
            'is_active': ['exact'],
            'credit_limit': ['gte', 'lte'],
            'created_at': ['gte', 'lte'],
        }
