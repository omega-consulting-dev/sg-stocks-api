from rest_framework import serializers
from apps.accounts.models import Notification


class MultipleSerializerMixin:

    serializer_detail_class = None

    def get_serializer_class(self):
        if self.action == 'retrieve' and self.serializer_detail_class is not None:
            return self.serializer_detail_class
        return super().get_serializer_class()


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications"""
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'type_display',
            'title',
            'message',
            'priority',
            'priority_display',
            'is_read',
            'read_at',
            'data',
            'action_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'read_at']


class MarkAsReadSerializer(serializers.Serializer):
    """Serializer pour marquer des notifications comme lues"""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Liste des IDs de notifications à marquer comme lues"
    )
    mark_all = serializers.BooleanField(
        default=False,
        help_text="Marquer toutes les notifications comme lues"
    )
