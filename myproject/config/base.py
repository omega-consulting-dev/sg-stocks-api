
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
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_HEADERS = list(default_headers) + env.list('CORS_ALLOW_HEADERS', default=[])
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
        "NAME": env("POSTGRES_DB", default="app"),
        "USER": env("POSTGRES_USER", default="app"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}


# Redis
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env('REDIS_URL', default='redis://localhost:6379/0'),
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

# Email
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='services@sg-stocks.com')

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("SIMPLE_JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=30))),
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
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
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

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'
 
# Application definition
SHARED_APPS = (
    'django_tenants',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.staticfiles',

    # External
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_filters',
    'corsheaders',
    'drf_yasg',
    'celery',

    # Local
    'apps.tenants',
    'apps.main',
    'core',
)

TENANT_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',

    # External
    'guardian',
    'auditlog',

    # Local
    'apps.accounts',
    'apps.products',
    'apps.services',
    'apps.inventory',
    'apps.sales',
    'apps.invoicing',
    'apps.customers',
    'apps.suppliers',
    'apps.cashbox',
    'apps.loans',
    'apps.expenses',
    'apps.analytics',
)
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'apps.tenants.middelware.TenantHeaderMiddleware',

    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'