"""
WebSocket consumers for real-time notifications.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.accounts.models import Notification
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        # Get tenant from scope (set by TenantWebSocketMiddleware)
        tenant = self.scope.get('tenant')
        if not tenant:
            await self.close()
            return
        
        self.tenant = tenant
        self.tenant_schema = tenant.schema_name
        
        # Get token from query parameters
        query_string = self.scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if not token:
            await self.close()
            return

        # Validate JWT token and get user
        user = await self.get_user_from_token(token)
        if not user:
            await self.close()
            return

        self.user = user
        
        # Create a unique group name for this user and tenant
        self.group_name = f"notifications_{self.tenant_schema}_{self.user.id}"
        
        # Join the user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial unread count
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count
        }))

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Validate JWT token and return user within tenant context."""
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            
            # Switch to tenant schema
            with schema_context(self.tenant_schema):
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated_token)
                
                if user and not user.is_anonymous:
                    return user
                
                return None
        except (InvalidToken, TokenError) as e:
            print(f"Token validation error: {e}")
            return None

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle messages from WebSocket."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Répondre au ping pour maintenir la connexion active
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
            elif message_type == 'get_unread_count':
                count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': count
                }))
        except json.JSONDecodeError:
            pass

    async def notification_new(self, event):
        """
        Send new notification to WebSocket.
        Called when a new notification is created.
        """
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }))

    async def notification_count(self, event):
        """
        Send updated unread count to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count']
        }))

    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for current user within tenant context."""
        with schema_context(self.tenant_schema):
            return Notification.objects.filter(
                user=self.user,
                is_read=False
            ).count()
