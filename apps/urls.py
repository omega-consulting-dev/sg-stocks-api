from django.urls import path, include

from apps.users.urls import urlpatterns as user_urls
from apps.tenants.urls import urlpatterns as tenant_urls


urlpatterns = [
    path('auth/', include(user_urls)),
    path('tenants/', include(tenant_urls))
]