
from pathlib import Path
import environ, os
from datetime import timedelta
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env(DEBUG=(bool, False))

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
CORS_ALLOW_ALL_ORIGINS = False  # Never use wildcard with credentials
CORS_ALLOWED_ORIGINS = []  # Will be set in dev.py/prod.py
CORS_ALLOWED_ORIGIN_REGEXES = []  # Will be set in dev.py/prod.py
CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-tenant',
    'x-tenant-schema',
    'x-tenant-name',
] + env.list('CORS_ALLOW_HEADERS', default=[])
CORS_ALLOW_CREDENTIALS = True

TENANT_BASE_DOMAIN = env('BASE_DOMAIN', default='localhost') # variable customiser pour faciliter la creation des domaines(tenant1 au lieux de tenant1.mydomain.com)
TENANT_MODEL = "tenants.Company"
TENANT_DOMAIN_MODEL = "tenants.Domain"
PUBLIC_SCHEMA_NAME = "public"
PUBLIC_SCHEMA_URLCONF = 'myproject.urls_public'
DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']

# Database
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": env("DB_NAME", default="app"),
        "USER": env("DB_USER", default="app"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}


# Redis
REDIS_HOST = env('REDIS_HOST', default='localhost')
REDIS_PORT = env('REDIS_PORT', default='6379')
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Session
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/2')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Douala'

# Pour le développement : exécuter les tâches de manière synchrone si Redis n'est pas disponible
# En production, mettez CELERY_TASK_ALWAYS_EAGER = False et lancez un worker Celery
CELERY_TASK_ALWAYS_EAGER = False  # Mode synchrone forcé
CELERY_TASK_EAGER_PROPAGATES = True

# Email - Configuration depuis variables d'environnement
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@sg-stocks.com')

# Cloudflare DNS Automation
CLOUDFLARE_API_TOKEN = env('CLOUDFLARE_API_TOKEN', default=None)
CLOUDFLARE_ZONE_ID = env('CLOUDFLARE_ZONE_ID', default=None)
SERVER_IP = env('SERVER_IP', default=None)

# Emails pour les notifications admin (messages de contact)
ADMIN_NOTIFICATION_EMAILS = env.list('ADMIN_NOTIFICATION_EMAILS', default=['admin@localhost'])

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("SIMPLE_JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=1440))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("SIMPLE_JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7))),
    # 'ROTATE_REFRESH_TOKENS': True,
    # 'BLACKLIST_AFTER_ROTATION': True,
    # 'UPDATE_LAST_LOGIN': True,
    # 'ALGORITHM': 'HS256',
    # 'SIGNING_KEY': SECRET_KEY,
    # 'AUTH_HEADER_TYPES': ('Bearer',),
    # 'USER_ID_FIELD': 'id',
    # 'USER_ID_CLAIM': 'user_id',
    # 'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    # 'TOKEN_TYPE_CLAIM': 'token_type',
}

# DRF Spectacular Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'SG-Stock API',
    'DESCRIPTION': 'API pour la gestion commerciale multi-tenant',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v1',
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.CustomPageNumberPagination',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

# django guardian
ANONYMOUS_USER_ID = -1

# Guardian pour permissions granulaires
AUTHENTICATION_BACKENDS = (
    # 'django.contrib.auth.backends.ModelBackend',
    'apps.main.backends.TenantAuthBackend',
    'guardian.backends.ObjectPermissionBackend',
)

ROOT_URLCONF = 'myproject.urls'

WSGI_APPLICATION = 'myproject.wsgi.application'
ASGI_APPLICATION = 'myproject.asgi.application'

# Channels - Using InMemory for development (Redis not available on Windows)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    },
}

# Pour production avec Redis, utiliser:
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {
#             "hosts": [env('REDIS_URL', default='redis://localhost:6379/3')],
#         },
#     },
# }

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuration du modèle User personnalisé pour les tenants
# Le modèle public garde le User Django par défaut
AUTH_USER_MODEL = 'accounts.User'  # Utilise accounts.User pour les tenants

AUDITLOG_LOGENTRY_MODEL = "auditlog.LogEntry"
# Application definition
SHARED_APPS = (
    # Django tenants DOIT être en premier
    'django_tenants',
    
    # Apps Django de base (dans l'ordre de dépendance)
    'django.contrib.contenttypes',  # Requis par auth et admin
    'django.contrib.auth',  # Requis par admin et accounts
    'django.contrib.sessions',
    'django.contrib.messages',
    
    # Apps locales
    'apps.tenants',  # Modèle de tenant utilisé partout
    'apps.accounts',  # Modèle User utilisé partout (AUTH_USER_MODEL)
    
    # Admin après accounts
    'django.contrib.admin',
    'django.contrib.staticfiles',

    # Apps externes
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_filters',
    'corsheaders',
    'drf_yasg',
    'celery',
    'channels',

    # Apps locales partagées
    'apps.main',
    # Note: 'core' est maintenant dans TENANT_APPS pour que chaque tenant ait ses propres configurations
)

TENANT_APPS = (
    # Django de base (dans l'ordre de dépendance)
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',

    # Apps locales (accounts doit être ici car il a des relations vers inventory)
    'apps.accounts',  # Contient des relations vers inventory.Store
    
    # Core app pour configurations tenant-specific
    'core',  # Notifications et configurations de champs par tenant
    
    # Apps externes (guardian dépend de auth)
    'guardian',
    'auditlog',

    # Apps métier (dans l'ordre logique de dépendance)
    'apps.products',  # Base: produits et services
    'apps.services',
    'apps.customers',  # Requis par sales et invoicing
    'apps.suppliers',  # Requis par inventory
    'apps.inventory',  # Utilise products et stores
    'apps.sales',  # Utilise products, customers, inventory
    'apps.invoicing',  # Utilise sales et customers
    'apps.cashbox',  # Utilise sales
    'apps.loans',  # Utilise customers
    'apps.expenses',  # Indépendant
    'apps.analytics',  # Utilise toutes les autres apps
)
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'apps.tenants.middelware.TenantHeaderMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Language selection middleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.accounts.middlewares.UserSessionMiddleware',
    'apps.accounts.middlewares.UserActivityMiddleware',
    'apps.accounts.middlewares.LoginLogoutMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
]



TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# Internationalization
LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Supported languages
LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
]

# Path to translation files
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Language cookie settings
LANGUAGE_COOKIE_NAME = 'django_language'
LANGUAGE_COOKIE_AGE = 365 * 24 * 60 * 60  # 1 year
LANGUAGE_COOKIE_PATH = '/'
LANGUAGE_COOKIE_DOMAIN = None
LANGUAGE_COOKIE_SECURE = False  # Set to True in production with HTTPS
LANGUAGE_COOKIE_HTTPONLY = False  # Set to True if you don't need JS access
LANGUAGE_COOKIE_SAMESITE = 'Lax'

# Middleware for language selection (add to MIDDLEWARE if not present)
# 'django.middleware.locale.LocaleMiddleware',

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'