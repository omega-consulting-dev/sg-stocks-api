from .base import *

DEBUG = False

# SSL/HTTPS Configuration
SECURE_SSL_REDIRECT = True  # Forcer HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Trust nginx X-Forwarded-Proto header
SESSION_COOKIE_SECURE = True  # Cookies sécurisés (HTTPS uniquement)
CSRF_COOKIE_SECURE = True  # CSRF cookies sécurisés

# CORS Configuration pour la production
CORS_ALLOW_ALL_ORIGINS = False

# Ajouter le support des sous-domaines dynamiques pour les tenants
# Format: https://omega.sg-stocks.com, https://api.sg-stocks.com, etc.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w-]+\.sg-stocks\.com$",  # Sous-domaines (omega.sg-stocks.com, api.sg-stocks.com)
    r"^https://sg-stocks\.com$",          # Domaine principal
]

# CSRF Trusted Origins pour les sous-domaines dynamiques
CSRF_TRUSTED_ORIGINS = [
    'https://*.sg-stocks.com',
    'https://sg-stocks.com',
]

CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Logging
LOGGING['handlers']['file']['filename'] = '/app/logs/django.log'