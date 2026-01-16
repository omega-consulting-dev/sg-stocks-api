"""
URLs for core app (notifications, field configurations)
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import NotificationViewSet
from core.views_field_config import FieldConfigurationViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'field-configurations', FieldConfigurationViewSet, basename='field-configurations')

urlpatterns = [
    path('', include(router.urls)),
]
