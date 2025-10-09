from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.main.views import RegisterView, LoginView


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh_token/', TokenRefreshView.as_view(), name='refresh_token'),
    # path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]