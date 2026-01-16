from rest_framework import serializers
from .models_contact import ContactMessage


class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages de contact"""
    
    class Meta:
        model = ContactMessage
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'message',
            'status',
            'response',
            'responded_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'responded_at']


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de messages de contact (depuis ApplicationSgStock)"""
    
    class Meta:
        model = ContactMessage
        fields = ['first_name', 'last_name', 'email', 'phone', 'message']


class ContactMessageResponseSerializer(serializers.Serializer):
    """Serializer pour répondre à un message"""
    response = serializers.CharField(required=True)
