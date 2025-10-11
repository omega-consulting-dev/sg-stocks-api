from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.services.views import ServiceViewSet, ServiceCategoryViewSet, ServiceInterventionViewSet

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'categories', ServiceCategoryViewSet, basename='service-category')
router.register(r'interventions', ServiceInterventionViewSet, basename='intervention')

urlpatterns = [
    path('', include(router.urls)),
]