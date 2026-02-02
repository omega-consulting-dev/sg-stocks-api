# tenants/urls.py
from django.urls import path, include
from .views import (
    TenantProvisioningView, 
    current_tenant, 
    renew_subscription, 
    change_plan,
    get_subscription_price,
    validate_payment,
    subscription_status
)
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, DomainReadOnlyViewSet

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'domains', DomainReadOnlyViewSet, basename='domain')

urlpatterns = [
    path('provisioning/', TenantProvisioningView.as_view(), name='tenant-provisioning'),
    path('current/', current_tenant, name='current-tenant'),
    
    # Gestion des abonnements
    path('subscription/renew/', renew_subscription, name='renew-subscription'),
    path('subscription/change-plan/', change_plan, name='change-plan'),
    path('subscription/price/', get_subscription_price, name='subscription-price'),
    path('subscription/validate-payment/', validate_payment, name='validate-payment'),
    path('subscription/status/', subscription_status, name='subscription-status'),
    
    path('', include(router.urls)),
]