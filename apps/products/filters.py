"""
Product filters for API.
"""

import django_filters
from apps.products.models import Product


class ProductFilter(django_filters.FilterSet):
    """Filter set for Product model."""
    
    name = django_filters.CharFilter(lookup_expr='icontains')
    reference = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.NumberFilter(field_name='category__id')
    min_price = django_filters.NumberFilter(field_name='selling_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='selling_price', lookup_expr='lte')
    is_for_sale = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    product_type = django_filters.ChoiceFilter(choices=Product.PRODUCT_TYPE_CHOICES)
    
    class Meta:
        model = Product
        fields = [
            'name', 'reference', 'category', 'min_price', 'max_price',
            'is_for_sale', 'is_active', 'product_type'
        ]