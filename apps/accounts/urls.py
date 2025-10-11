"""
Accounts URLs configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from apps.accounts.views import LoginView
from apps.accounts.views import (
    UserViewSet,
    RoleViewSet,
    PermissionViewSet,
    UserSessionViewSet,
    UserActivityViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'sessions', UserSessionViewSet, basename='session')
router.register(r'activities', UserActivityViewSet, basename='activity')

urlpatterns = [
    # JWT Authentication
    # path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Router URLs
    path('', include(router.urls)),
]