# from rest_framework import viewsets
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from django.db.models import Sum, F, Value, Q, DecimalField
# from django.db.models.functions import Coalesce

# from apps.accounts.models import User
# from apps.accounts.serializers import UserListSerializer, UserDetailSerializer
# from apps.suppliers.models import Supplier
# from apps.suppliers.views_payment import SupplierPaymentViewSet


# class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
#     """
#     ViewSet for suppliers (read-only).
#     Uses User model with is_supplier=True
#     """
#     permission_classes = []
    
#     def get_queryset(self):
#         return User.objects.filter(is_supplier=True)
    
#     def get_serializer_class(self):
#         if self.action == 'list':
#             return UserListSerializer
#         return UserDetailSerializer
    
#     @action(detail=False, methods=['get'])
#     def debts(self, request):
#         """
#         Liste les fournisseurs avec solde dû pour le tenant courant.
#         GET /api/v1/suppliers/debts/
#         Retourne les fournisseurs liés à des PurchaseOrder avec un solde non réglé.
#         Les données sont automatiquement filtrées par le tenant actuel (django-tenants).
#         """
#         # Annoter les Suppliers avec total_ordered et total_paid depuis PurchaseOrders confirmées
#         # Utiliser output_field=DecimalField pour éviter les erreurs de type mixte
#         # Inclure les PO en status 'received' (réception automatique) et 'confirmed'
#         statuses = ['confirmed', 'received']
#         queryset = Supplier.objects.annotate(
#             total_ordered=Coalesce(
#                 Sum('purchase_orders__total_amount', filter=Q(purchase_orders__status__in=statuses), output_field=DecimalField()), 
#                 Value(0, output_field=DecimalField())
#             ),
#             total_paid=Coalesce(
#                 Sum('purchase_orders__paid_amount', filter=Q(purchase_orders__status__in=statuses), output_field=DecimalField()), 
#                 Value(0, output_field=DecimalField())
#             ),
#         ).annotate(
#             balance=F('total_ordered') - F('total_paid')
#         ).filter(balance__gt=0).order_by('-balance')
        
#         # Construire la réponse
#         data = [
#             {
#                 'id': s.id,
#                 'supplier_code': s.supplier_code,
#                 'name': s.name,
#                 'email': s.email,
#                 'phone': s.phone,
#                 'total_ordered': float(s.total_ordered or 0),
#                 'total_paid': float(s.total_paid or 0),
#                 'balance': float(s.balance or 0),
#             }
#             for s in queryset
#         ]
#         return Response(data)


# __all__ = ['SupplierViewSet', 'SupplierPaymentViewSet']
