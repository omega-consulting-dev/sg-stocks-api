from django.urls import path, include

from apps.users.urls import urlpatterns as user_urls


urlpatterns = [
    path('', include(user_urls)),
]