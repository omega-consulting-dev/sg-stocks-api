from .base import *

DEBUG = True

# CORS Configuration pour le développement
# Note: CORS_ALLOW_ALL_ORIGINS = True n'est pas compatible avec credentials
# On doit spécifier explicitement les origines autorisées
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
]

# Ajouter dynamiquement les sous-domaines *.localhost pour les tenants
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://[\w-]+\.localhost:5173$",
    r"^http://[\w-]+\.localhost:5174$",
]

ALLOWED_HOSTS = ['*']

# Debug Toolbar
INSTALLED_APPS += ['debug_toolbar', 'django_extensions']

MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Email backend for development - SMTP activé pour tester l'envoi réel
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Disable HTTPS redirect in development
SECURE_SSL_REDIRECT = False