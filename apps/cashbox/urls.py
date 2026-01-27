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
    DecaissementsExportPDFView,
    StoreListView,
    BankTransactionsListView,
    BankWithdrawalCreateView,
    BankTransactionsExportPDFView,
    BankTransactionsExportExcelView,
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
    path('decaissements/export-pdf/', DecaissementsExportPDFView.as_view(), name='decaissements-export-pdf'),
    path('bank-transactions/', BankTransactionsListView.as_view(), name='bank-transactions-list'),
    path('bank-transactions/withdraw/', BankWithdrawalCreateView.as_view(), name='bank-withdrawal-create'),
    path('bank-transactions/export-pdf/', BankTransactionsExportPDFView.as_view(), name='bank-transactions-export-pdf'),
    path('bank-transactions/export-excel/', BankTransactionsExportExcelView.as_view(), name='bank-transactions-export-excel'),
    path('', include(router.urls)),
]
