from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.suppliers.models import SupplierPayment
from apps.suppliers.serializers import SupplierPaymentSerializer


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    """Manage supplier payments (create/list/retrieve)."""
    queryset = SupplierPayment.objects.all()
    serializer_class = SupplierPaymentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """Return payments for current tenant (django-tenants handles schema isolation)."""
        return SupplierPayment.objects.all()

    def perform_create(self, serializer):
        """Create payment and attach current user as creator."""
        serializer.save(created_by=self.request.user)
