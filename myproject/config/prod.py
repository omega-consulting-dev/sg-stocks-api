from .base import *

DEBUG = False
# TODO: Enable after SSL configuration
SECURE_SSL_REDIRECT = False

# CORS Configuration pour la production
CORS_ALLOW_ALL_ORIGINS = False

# Ajouter le support des sous-domaines dynamiques pour les tenants
# Format: https://tenant1.sgstocks.com, https://tenant2.sgstocks.com, etc.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.sg-stocks\.com$",  # Sous-domaines (HTTP et HTTPS)
    r"^https?://sg-stocks\.com$",          # Domaine principal
]

# TODO: Enable after SSL configuration
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
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