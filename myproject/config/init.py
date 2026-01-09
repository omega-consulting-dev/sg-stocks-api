"""
Settings pour l'initialisation de la base de données.
Utilise le backend PostgreSQL standard au lieu de django-tenants pour éviter
le problème circulaire lors des migrations initiales.
"""

from .dev import *

# Remplacer le backend django-tenants par le backend PostgreSQL standard
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",  # Backend standard au lieu de django_tenants
        "NAME": env("POSTGRES_DB", default="app"),
        "USER": env("POSTGRES_USER", default="app"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# Désactiver le middleware django-tenants
MIDDLEWARE = [m for m in MIDDLEWARE if 'django_tenants' not in m and 'TenantHeaderMiddleware' not in m]

# Désactiver le router de django-tenants
DATABASE_ROUTERS = []
