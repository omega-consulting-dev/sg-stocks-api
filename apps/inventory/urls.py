from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.inventory.views import (
    StoreViewSet, StockViewSet, StockMovementViewSet,
    StockTransferViewSet, InventoryViewSet
)


router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'stocks', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='movement')
router.register(r'transfers', StockTransferViewSet, basename='transfer')
router.register(r'inventories', InventoryViewSet, basename='inventory')

urlpatterns = [
    path('', include(router.urls)),
]