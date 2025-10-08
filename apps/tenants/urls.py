# tenants/urls.py
from django.urls import path, include
from .views import TenantProvisioningView
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, DomainReadOnlyViewSet

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'domains', DomainReadOnlyViewSet, basename='domain')

urlpatterns = [
    path('provisioning/', TenantProvisioningView.as_view(), name='tenant-provisioning'),
    path('', include(router.urls)),
]