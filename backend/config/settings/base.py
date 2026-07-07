"""Base Django settings shared by every environment.

Environment-specific modules (development, production, testing) import ``*``
from here and override. All externalized configuration is read through the
strongly-typed Pydantic ``Settings`` object (see ``env.py``) — never via
ad-hoc ``os.environ`` access (ARCH-001 §16.3).

This is infrastructure configuration only: it wires Django, DRF, JWT, CORS,
static/media, and the bounded-context apps. It contains no business logic.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from .env import get_settings

settings = get_settings()

# backend/ (parent of config/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Security -------------------------------------------------------------
SECRET_KEY = settings.secret_key
DEBUG = settings.debug
ALLOWED_HOSTS = settings.allowed_hosts

# --- Applications ---------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    # Refresh-token blacklist (rotation + logout revocation, API-000 §17.2).
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
]

# Bounded contexts (modular monolith — ARCH-001 §14). Each maps to a
# PostgreSQL schema at the persistence layer (ARCH-001 §9.2).
LOCAL_APPS = [
    "apps.identity",
    "apps.participants",
    "apps.institutions",
    "apps.competitions",
    "apps.applications",
    "apps.performances",
    "apps.judging",
    "apps.results",
    "apps.finance",
    "apps.notifications",
    "apps.analytics",
    "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware -----------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database (ARCH-001 §9) ----------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": settings.database.db,
        "USER": settings.database.user,
        "PASSWORD": settings.database.password,
        "HOST": settings.database.host,
        "PORT": str(settings.database.port),
        "CONN_MAX_AGE": 60,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Migrations live under each bounded context's infrastructure layer (ARCH-001
# §7.2, §9.2, §14), not the default ``<app>/migrations/``.
MIGRATION_MODULES = {
    "identity": "apps.identity.infrastructure.migrations",
}

# --- Password validation --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Argon2 preferred for password hashing (ARCH-001 §11.2).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# --- Localization (timezone UTC, language ru) -----------------------------
LANGUAGE_CODE = settings.language_code
TIME_ZONE = settings.time_zone
USE_I18N = True
USE_TZ = True

# --- Static & media -------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS: list[Path] = []

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --- REST Framework (API-000) --------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        # Deny by default (ARCH-001 §12.4, API-000 §18).
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ),
    # Cursor pagination is the platform default (API-000 §9).
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "1000/min"},
}

# --- JWT (ARCH-001 §11, API-000 §17) --------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=settings.jwt.access_token_lifetime_minutes),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=settings.jwt.refresh_token_lifetime_days),
    "ROTATE_REFRESH_TOKENS": settings.jwt.rotate_refresh_tokens,
    "BLACKLIST_AFTER_ROTATION": settings.jwt.blacklist_after_rotation,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Refresh token cookie (web clients): httpOnly + Secure + SameSite so the token is
# never readable by JS and never sent cross-site (ARCH-001 §11.1, API-001 §1.2).
# Native clients ignore the cookie and use the response body instead.
REFRESH_TOKEN_COOKIE = {
    "NAME": "refresh_token",
    "PATH": "/api/v1/auth",
    "HTTPONLY": True,
    "SECURE": not DEBUG,
    "SAMESITE": "Strict",
}

# --- OpenAPI 3.1 schema (drf-spectacular, API-000 §25) --------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "VT Platform API",
    "DESCRIPTION": "«Взлёт талантов» — REST API for children's creative competitions.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]",
    "OAS_VERSION": "3.1.0",
}

# --- CORS (locked to known origins, API-000 §26) --------------------------
CORS_ALLOWED_ORIGINS = settings.cors_allowed_origins
CORS_ALLOW_CREDENTIALS = True

# --- Cache & Celery (Redis; ARCH-001 §6.1, §7.5) --------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": str(settings.redis_url),
    }
}

CELERY_BROKER_URL = str(settings.celery_broker_url)
CELERY_RESULT_BACKEND = str(settings.celery_result_backend)
CELERY_TASK_TRACK_STARTED = True
CELERY_TIMEZONE = TIME_ZONE

# --- Logging: structured, no PII (ARCH-001 §19) ---------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
