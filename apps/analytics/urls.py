from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.analytics.views import DashboardViewSet

router = DefaultRouter()
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]