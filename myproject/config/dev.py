from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

ALLOWED_HOSTS = ['*']

# Debug Toolbar
INSTALLED_APPS += ['debug_toolbar', 'django_extensions']

MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable HTTPS redirect in development
SECURE_SSL_REDIRECT = False