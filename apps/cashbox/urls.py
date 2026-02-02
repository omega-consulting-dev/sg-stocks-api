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
    BankDepositCreateView,
    BankTransactionsExportPDFView,
    BankTransactionsExportExcelView,
    MobileMoneyBalanceView,
    MobileMoneyTransactionsListView,
    MobileMoneyDepositCreateView,
    MobileMoneyWithdrawalCreateView,
    MobileMoneyTransactionsExportPDFView,
    MobileMoneyTransactionsExportExcelView,
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
    path('bank-transactions/deposit/', BankDepositCreateView.as_view(), name='bank-deposit-create'),
    path('bank-transactions/export-pdf/', BankTransactionsExportPDFView.as_view(), name='bank-transactions-export-pdf'),
    path('bank-transactions/export-excel/', BankTransactionsExportExcelView.as_view(), name='bank-transactions-export-excel'),
    path('mobile-money/balance/', MobileMoneyBalanceView.as_view(), name='mobile-money-balance'),
    path('mobile-money/transactions/', MobileMoneyTransactionsListView.as_view(), name='mobile-money-transactions'),
    path('mobile-money/deposit/', MobileMoneyDepositCreateView.as_view(), name='mobile-money-deposit'),
    path('mobile-money/withdraw/', MobileMoneyWithdrawalCreateView.as_view(), name='mobile-money-withdraw'),
    path('mobile-money/export-pdf/', MobileMoneyTransactionsExportPDFView.as_view(), name='mobile-money-export-pdf'),
    path('mobile-money/export-excel/', MobileMoneyTransactionsExportExcelView.as_view(), name='mobile-money-export-excel'),
    path('', include(router.urls)),
]
