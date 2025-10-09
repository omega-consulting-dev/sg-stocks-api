from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include

from myproject import config

import os
route_doc = []
if os.getenv("ENV_NAME", "dev") == "dev":

    from drf_yasg.views import get_schema_view
    from drf_yasg import openapi
    from rest_framework import permissions

    schema_view = get_schema_view(
        openapi.Info(
            title="API Documentation",
            default_version="v1",
            description="Description de votre API",
            terms_of_service="https://www.google.com/policies/terms/",
            contact=openapi.Contact(email="votre_email@example.com"),
            license=openapi.License(name="MIT License"),
        ),
        public=True,
        permission_classes=(permissions.AllowAny,),
    )
    route_doc = [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]

urlpatterns = [
    *route_doc,
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.urls_public')),
] + static(config.MEDIA_URL, document_root=config.MEDIA_ROOT)
