from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.loans.views import LoanViewSet, LoanPaymentViewSet

router = DefaultRouter()
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'payments', LoanPaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
]