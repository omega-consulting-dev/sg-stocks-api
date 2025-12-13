"""
Supplier filters for API.
"""

import django_filters
from apps.suppliers.models import Supplier


class SupplierFilter(django_filters.FilterSet):
    """Filter set for Supplier model."""
    
    # Text search filters
    supplier_code = django_filters.CharFilter(lookup_expr='icontains')
    name = django_filters.CharFilter(lookup_expr='icontains')
    contact_person = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    phone = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(lookup_expr='icontains')
    country = django_filters.CharFilter(lookup_expr='icontains')
    
    # Exact match filters
    payment_term = django_filters.ChoiceFilter(choices=Supplier.PAYMENT_TERM_CHOICES)
    rating = django_filters.NumberFilter()
    is_active = django_filters.BooleanFilter()
    
    # Range filters
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    rating_max = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    
    # Date filters
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Supplier
        fields = {
            'supplier_code': ['exact', 'icontains'],
            'name': ['exact', 'icontains'],
            'contact_person': ['exact', 'icontains'],
            'email': ['exact', 'icontains'],
            'phone': ['exact', 'icontains'],
            'city': ['exact', 'icontains'],
            'country': ['exact', 'icontains'],
            'payment_term': ['exact'],
            'rating': ['exact', 'gte', 'lte'],
            'is_active': ['exact'],
            'created_at': ['gte', 'lte'],
        }
