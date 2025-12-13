from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.loans.views import LoanViewSet, LoanPaymentViewSet, LoanExportExcelView

router = DefaultRouter()
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'payments', LoanPaymentViewSet, basename='payment')

urlpatterns = [
    path('loans/export_excel/', LoanExportExcelView.as_view(), name='loan-export-excel'),
    path('', include(router.urls)),
]