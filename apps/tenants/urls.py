# tenants/urls.py
from django.urls import path, include
from .views import TenantProvisioningView, current_tenant, renew_subscription, change_plan
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, DomainReadOnlyViewSet

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'domains', DomainReadOnlyViewSet, basename='domain')

urlpatterns = [
    path('provisioning/', TenantProvisioningView.as_view(), name='tenant-provisioning'),
    path('current/', current_tenant, name='current-tenant'),
    path('subscription/renew/', renew_subscription, name='renew-subscription'),
    path('subscription/change-plan/', change_plan, name='change-plan'),
    path('', include(router.urls)),
]