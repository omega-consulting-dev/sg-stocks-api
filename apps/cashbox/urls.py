from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.cashbox.views import (
    CashboxViewSet, 
    CashboxSessionViewSet, 
    CashMovementViewSet,
    EncaissementsListView,
    EncaissementsExportView,
    CaisseSoldeView,
    DecaissementsListView,
    DecaissementsExportView,
    StoreListView,
)

router = DefaultRouter()
router.register(r'cashboxes', CashboxViewSet, basename='cashbox')
router.register(r'sessions', CashboxSessionViewSet, basename='session')
router.register(r'movements', CashMovementViewSet, basename='movement')

urlpatterns = [
    path('stores/', StoreListView.as_view(), name='stores-list'),
    path('encaissements/', EncaissementsListView.as_view(), name='encaissements-list'),
    path('encaissements/export/', EncaissementsExportView.as_view(), name='encaissements-export'),
    path('caisse/solde/', CaisseSoldeView.as_view(), name='caisse-solde'),
    path('decaissements/', DecaissementsListView.as_view(), name='decaissements-list'),
    path('decaissements/export/', DecaissementsExportView.as_view(), name='decaissements-export'),
    path('', include(router.urls)),
]
