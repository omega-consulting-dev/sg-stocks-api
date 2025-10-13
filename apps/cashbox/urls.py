from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.cashbox.views import CashboxViewSet, CashboxSessionViewSet, CashMovementViewSet

router = DefaultRouter()
router.register(r'cashboxes', CashboxViewSet, basename='cashbox')
router.register(r'sessions', CashboxSessionViewSet, basename='session')
router.register(r'movements', CashMovementViewSet, basename='movement')

urlpatterns = [
    path('', include(router.urls)),
]