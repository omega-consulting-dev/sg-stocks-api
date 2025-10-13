from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.cashbox.models import Cashbox, CashboxSession, CashMovement
from apps.cashbox.serializers import CashboxSerializer, CashboxSessionSerializer, CashMovementSerializer


class CashboxViewSet(viewsets.ModelViewSet):
    queryset = Cashbox.objects.select_related('store')
    serializer_class = CashboxSerializer
    filterset_fields = ['store', 'is_active']


class CashboxSessionViewSet(viewsets.ModelViewSet):
    queryset = CashboxSession.objects.select_related('cashbox', 'cashier')
    serializer_class = CashboxSessionSerializer
    filterset_fields = ['cashbox', 'cashier', 'status']
    
    @action(detail=False, methods=['post'])
    def open_session(self, request):
        """Open a new cashbox session."""
        cashbox_id = request.data.get('cashbox')
        opening_balance = request.data.get('opening_balance', 0)
        
        # Check if there's already an open session
        if CashboxSession.objects.filter(cashbox_id=cashbox_id, status='open').exists():
            return Response(
                {'error': 'Une session est déjà ouverte pour cette caisse.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = CashboxSession.objects.create(
            cashbox_id=cashbox_id,
            cashier=request.user,
            opening_date=timezone.now(),
            opening_balance=opening_balance,
            status='open',
            created_by=request.user
        )
        
        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def close_session(self, request, pk=None):
        """Close a cashbox session."""
        session = self.get_object()
        
        if session.status != 'open':
            return Response(
                {'error': 'Cette session est déjà fermée.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        actual_balance = request.data.get('actual_closing_balance')
        closing_notes = request.data.get('closing_notes', '')
        
        # Calculate expected balance
        from django.db.models import Sum, Case, When, F
        movements = CashMovement.objects.filter(cashbox_session=session)
        total_in = movements.filter(movement_type='in').aggregate(total=Sum('amount'))['total'] or 0
        total_out = movements.filter(movement_type='out').aggregate(total=Sum('amount'))['total'] or 0
        
        session.expected_closing_balance = session.opening_balance + total_in - total_out
        session.actual_closing_balance = actual_balance
        session.closing_date = timezone.now()
        session.closing_notes = closing_notes
        session.status = 'closed'
        session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)


class CashMovementViewSet(viewsets.ModelViewSet):
    queryset = CashMovement.objects.select_related('cashbox_session', 'sale')
    serializer_class = CashMovementSerializer
    filterset_fields = ['cashbox_session', 'movement_type', 'category', 'payment_method']
    
    def perform_create(self, serializer):
        # Generate movement number
        count = CashMovement.objects.count() + 1
        movement = serializer.save(
            movement_number=f"MVT{count:08d}",
            created_by=self.request.user
        )