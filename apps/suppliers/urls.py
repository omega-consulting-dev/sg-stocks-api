from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.suppliers.views import SupplierViewSet, SupplierPaymentViewSet

# Two routers with explicit prefixes, both included at root
supplier_router = DefaultRouter()
supplier_router.register(r'suppliers', SupplierViewSet, basename='supplier')

payment_router = DefaultRouter()
payment_router.register(r'payments', SupplierPaymentViewSet, basename='supplierpayment')

urlpatterns = [
    path('', include(supplier_router.urls)),
    path('', include(payment_router.urls)),
]