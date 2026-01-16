from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone

from .models_contact import ContactMessage
from .serializers_contact import (
    ContactMessageSerializer,
    ContactMessageCreateSerializer,
    ContactMessageResponseSerializer
)
from .tasks import send_contact_response_email, send_new_contact_notification
from .emails import send_contact_response_email, send_new_contact_notification


class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les messages de contact
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    
    def get_permissions(self):
        """
        Permissions :
        - AllowAny pour create (depuis ApplicationSgStock)
        - IsAuthenticated pour le reste (depuis AdminSgStock)
        """
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        """Utiliser le bon serializer selon l'action"""
        if self.action == 'create':
            return ContactMessageCreateSerializer
        elif self.action == 'respond':
            return ContactMessageResponseSerializer
        return ContactMessageSerializer
    
    def create(self, request, *args, **kwargs):
        """Créer un nouveau message de contact"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact_message = serializer.save()
        
        # Envoyer une notification aux admins de manière asynchrone
        send_new_contact_notification.delay({
            'first_name': contact_message.first_name,
            'last_name': contact_message.last_name,
            'email': contact_message.email,
            'phone': contact_message.phone,
            'message': contact_message.message,
        })
        
        return Response({
            'success': True,
            'message': 'Votre message a été envoyé avec succès. Nous vous contacterons bientôt.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """Récupérer un message et le marquer comme lu"""
        instance = self.get_object()
        instance.mark_as_read()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Répondre à un message de contact"""
        message = self.get_object()
        serializer = ContactMessageResponseSerializer(data=request.data)
        
        if serializer.is_valid():
            response_text = serializer.validated_data['response']
            message.mark_as_replied(response_text)
            
            # Envoyer un email au client de manière asynchrone avec Celery
            contact_data = {
                'first_name': message.first_name,
                'last_name': message.last_name,
                'email': message.email,
                'message': message.message,
            }
            
            # Lancer la tâche Celery en arrière-plan
            task = send_contact_response_email.delay(contact_data, response_text)
            
            return Response({
                'success': True,
                'message': 'Réponse enregistrée et email envoyé en arrière-plan',
                'task_id': task.id,
                'data': ContactMessageSerializer(message).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marquer un message comme lu"""
        message = self.get_object()
        message.mark_as_read()
        return Response({
            'success': True,
            'message': 'Message marqué comme lu',
            'data': ContactMessageSerializer(message).data
        })
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archiver un message"""
        message = self.get_object()
        message.status = 'archived'
        message.save()
        return Response({
            'success': True,
            'message': 'Message archivé',
            'data': ContactMessageSerializer(message).data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtenir les statistiques des messages"""
        total = ContactMessage.objects.count()
        new = ContactMessage.objects.filter(status='new').count()
        read = ContactMessage.objects.filter(status='read').count()
        replied = ContactMessage.objects.filter(status='replied').count()
        archived = ContactMessage.objects.filter(status='archived').count()
        
        return Response({
            'total': total,
            'new': new,
            'read': read,
            'replied': replied,
            'archived': archived,
        })
