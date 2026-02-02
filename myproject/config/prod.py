from .base import *

DEBUG = False
SECURE_SSL_REDIRECT = True

# CORS Configuration pour la production
CORS_ALLOW_ALL_ORIGINS = False

# Ajouter le support des sous-domaines dynamiques pour les tenants
# Format: https://tenant1.sgstocks.com, https://tenant2.sgstocks.com, etc.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w-]+\.sgstocks\.com$",  # Sous-domaines des tenants
]

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
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
LOGGING['handlers']['file']['filename'] = '/var/log/sgstock/django.log'