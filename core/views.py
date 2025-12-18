from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.accounts.models import Notification
from .serializers import NotificationSerializer, MarkAsReadSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour gérer les notifications de l'utilisateur connecté
    
    list: Récupérer toutes les notifications
    retrieve: Récupérer une notification spécifique
    unread_count: Compter les notifications non lues
    mark_as_read: Marquer des notifications comme lues
    mark_all_as_read: Marquer toutes les notifications comme lues
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Récupérer uniquement les notifications de l'utilisateur connecté.
        Pour les caissiers (access_scope='own'), filtrer aussi par entités accessibles.
        """
        user = self.request.user
        queryset = Notification.objects.filter(user=user)
        
        # Filtrage additionnel pour les caissiers avec access_scope='own'
        if hasattr(user, 'role') and user.role and user.role.access_scope == 'own':
            # Les caissiers voient uniquement les notifications liées à:
            # - Leurs propres ventes
            # - Leurs propres factures
            # - Leurs propres clients
            # - Leurs propres transactions
            # Note: Le champ related_object_id permet de lier la notification à une entité
            # Pour l'instant, on garde toutes les notifications de l'utilisateur
            # car elles sont déjà filtrées par user dans la requête de base
            pass
        
        # Filtrer par type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(type=notification_type)
        
        # Filtrer par statut de lecture
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            if is_read.lower() == 'true':
                queryset = queryset.filter(is_read=True)
            elif is_read.lower() == 'false':
                queryset = queryset.filter(is_read=False)
        
        # Filtrer par priorité
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        return queryset.select_related('user')
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Compter les notifications non lues"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return Response({'count': count})
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marquer une notification comme lue"""
        notification = self.get_object()
        
        if notification.user != request.user:
            return Response(
                {'error': 'Vous ne pouvez pas modifier cette notification'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification.mark_as_read()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_multiple_as_read(self, request):
        """Marquer plusieurs notifications comme lues"""
        serializer = MarkAsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data.get('mark_all'):
            # Marquer toutes les notifications comme lues
            updated = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
            return Response({
                'message': f'{updated} notification(s) marquée(s) comme lue(s)',
                'count': updated
            })
        
        notification_ids = serializer.validated_data.get('notification_ids', [])
        if notification_ids:
            updated = Notification.objects.filter(
                user=request.user,
                id__in=notification_ids,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
            return Response({
                'message': f'{updated} notification(s) marquée(s) comme lue(s)',
                'count': updated
            })
        
        return Response(
            {'error': 'Aucune notification à marquer'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['delete'])
    def delete_read(self, request):
        """Supprimer toutes les notifications lues"""
        deleted, _ = Notification.objects.filter(
            user=request.user,
            is_read=True
        ).delete()
        
        return Response({
            'message': f'{deleted} notification(s) supprimée(s)',
            'count': deleted
        })
