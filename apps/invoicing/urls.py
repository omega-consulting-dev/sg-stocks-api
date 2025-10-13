from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.invoicing.views import InvoiceViewSet, InvoicePaymentViewSet

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', InvoicePaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
]