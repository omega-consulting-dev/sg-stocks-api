from django.urls import path, include
from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from apps.main.views import RegisterView
from apps.main.views_superadmin import SuperAdminLoginView
from apps.main.views_settings import CompanySettingsViewSet, get_languages, set_language
from apps.main.views_users import PublicUserViewSet
from core.views import NotificationViewSet

router = DefaultRouter()
router.register(r'settings', CompanySettingsViewSet, basename='company-settings')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'users', PublicUserViewSet, basename='public-users')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', SuperAdminLoginView.as_view(), name='superadmin_login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Language management endpoints
    path('languages/', get_languages, name='get-languages'),
    path('set-language/', set_language, name='set-language'),
    
    path('', include(router.urls)),
]