"""
URLs pour l'interface superadmin.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .superadmin_views import (
    SuperAdminCompanyViewSet,
    SuperAdminBillingViewSet,
    SuperAdminAuditLogViewSet,
    SuperAdminSupportViewSet,
    SuperAdminDashboardViewSet
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'companies', SuperAdminCompanyViewSet, basename='superadmin-companies')
router.register(r'billing', SuperAdminBillingViewSet, basename='superadmin-billing')
router.register(r'audit-logs', SuperAdminAuditLogViewSet, basename='superadmin-audit')
router.register(r'support', SuperAdminSupportViewSet, basename='superadmin-support')
router.register(r'dashboard', SuperAdminDashboardViewSet, basename='superadmin-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]