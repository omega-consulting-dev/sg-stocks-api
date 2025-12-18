"""
WebSocket URL routing for accounts app.
"""
from django.urls import re_path
from apps.accounts.consumers import NotificationConsumer

websocket_urlpatterns = [
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
]
