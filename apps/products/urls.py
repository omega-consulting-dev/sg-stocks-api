"""
Product URLs configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.products.views import ProductViewSet, ProductCategoryViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', ProductCategoryViewSet, basename='product-category')

urlpatterns = [
    path('', include(router.urls)),
]