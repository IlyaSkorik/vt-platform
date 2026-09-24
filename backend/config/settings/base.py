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
from typing import Any

from corsheaders.defaults import default_headers

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
    # The platform operator's own context: who runs the platform above every
    # organization, and what each connected organization owes it.
    "apps.platform",
    "apps.organization",
    "apps.participants",
    "apps.institutions",
    "apps.competitions",
    "apps.applications",
    "apps.diplomas",
    "apps.teachers",
    "apps.performances",
    # The running order of the event itself (programs, their items, public links).
    "apps.programs",
    "apps.judging",
    "apps.results",
    # The audience's own verdict. The one context that works without a festival
    # on the platform: a ballot belongs to an organization, and its competition
    # is optional (see apps/voting/apps.py).
    "apps.voting",
    # What the audience said afterwards: one page per organization, reached from a
    # code on a banner (see apps/reviews/apps.py). Nothing it collects is published.
    "apps.reviews",
    # The platform's own books: what it spent, and on what. The income side is
    # derived from the organizations' terms and typed in by nobody; this is the
    # half that has to be entered by hand (see apps/finance/apps.py).
    "apps.finance",
    "apps.notifications",
    "apps.analytics",
    "apps.audit",
    # Composition edge — owns no domain; composes cross-context read models
    # (e.g. GET /users/me = Identity account + Organization staff status).
    "apps.composition",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware -----------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # After SecurityMiddleware so a plain-HTTP request is still redirected to HTTPS
    # rather than being asked for a password it would then send unencrypted; before
    # everything else so an unauthenticated request costs a session lookup and a
    # database connection it does not need. Removes itself when unconfigured, which
    # is every deployment except the stand.
    "config.middleware.SiteGateMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # Listed before XFrameOptions so it runs *after* it on the response and can
    # clear DENY for /media/** (PDF/image previews in the staff SPA iframe).
    "config.middleware.AllowMediaFramingMiddleware",
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
    "platform": "apps.platform.infrastructure.migrations",
    "organization": "apps.organization.infrastructure.migrations",
    "participants": "apps.participants.infrastructure.migrations",
    "competitions": "apps.competitions.infrastructure.migrations",
    "teachers": "apps.teachers.infrastructure.migrations",
    "applications": "apps.applications.infrastructure.migrations",
    "diplomas": "apps.diplomas.infrastructure.migrations",
    "programs": "apps.programs.infrastructure.migrations",
    "results": "apps.results.infrastructure.migrations",
    "notifications": "apps.notifications.infrastructure.migrations",
    "voting": "apps.voting.infrastructure.migrations",
    "reviews": "apps.reviews.infrastructure.migrations",
    "finance": "apps.finance.infrastructure.migrations",
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

#: Leading slash on purpose: every stored file reference is minted by
#: ``default_storage.url(key)``, and with a relative ``MEDIA_URL`` those would come out
#: without one and stop resolving against the API origin.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

#: Where a host keeps local copies of uploaded diploma fonts.
#:
#: reportlab embeds a font by opening a file, so a font in object storage has to be on the
#: local disk before it can be drawn. Left empty the cache lands in the system temp directory,
#: which is right for a single host; a container deployment should point this at a volume its
#: workers share, so a font is fetched from the bucket once per host rather than once per
#: container lifetime. It holds nothing that cannot be re-downloaded.
DIPLOMA_FONT_CACHE_DIR = settings.diploma_font_cache_dir

#: Annotated because the S3 entry below carries nested ``OPTIONS``, which a literal of
#: plain strings would otherwise fix the type of.
STORAGES: dict[str, dict[str, Any]] = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Uploads and generated documents move to object storage as soon as a bucket is
# configured. Nothing in the application layer knows: files are written through
# ``default_storage`` everywhere, and every reference is whatever that storage says its
# URL is - a ``/media/…`` path locally, an absolute bucket URL in a deployment.
if settings.s3_bucket:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": settings.s3_bucket,
            **({"region_name": settings.s3_region} if settings.s3_region else {}),
            **({"endpoint_url": settings.s3_endpoint_url} if settings.s3_endpoint_url else {}),
            **({"access_key": settings.s3_access_key_id} if settings.s3_access_key_id else {}),
            **({"secret_key": settings.s3_secret_access_key} if settings.s3_secret_access_key else {}),
            **({"custom_domain": settings.s3_custom_domain} if settings.s3_custom_domain else {}),
            **({"location": settings.s3_location} if settings.s3_location else {}),
            # Plain, stable URLs rather than signed ones: the bucket is public-read and a
            # reference is stored in the database, so it has to keep working tomorrow.
            "querystring_auth": False,
            # No ACL on the object. Public access is granted by the bucket policy, which is
            # the only thing that works on providers that disable object ACLs outright.
            "default_acl": None,
            # Two writes to one key are always a deliberate replacement in this codebase
            # (the callers delete first), so never rename behind their back - a renamed
            # object would leave the reference in the database pointing at nothing.
            "file_overwrite": True,
            # Keys carry an unguessable component and content at a key never changes
            # meaning, so a year is safe and it is what makes a CDN worth putting in front.
            "object_parameters": {"CacheControl": "public, max-age=31536000, immutable"},
        },
    }

# --- REST Framework (API-000) --------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
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
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "1000/min",
        # Casting a vote gets its own, far smaller bucket. A person in a hall
        # sends one request; whatever sends sixty a minute is not a person.
        # Deliberately not a fraud control — it is a brake, and the real rule is
        # the unique index on the votes table.
        "ballot_vote": "12/min",
        # Leaving a review gets its own bucket too, and a smaller one: writing a
        # note takes a minute, and the request carries photographs. Whatever sends
        # six a minute is not somebody standing at a banner.
        "review_submit": "6/min",
    },
    # Whatever DRF itself refuses (throttling, a wrong method, a malformed body) is
    # answered in Russian too, not only what a context's problems.py renders.
    "EXCEPTION_HANDLER": "config.api_errors.exception_handler",
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
    # Several serializers expose the same document-kind choice set under different
    # field names (`type` on a template, `documentType` on an assignment). Without
    # an override, spectacular resolves the collision with a hash suffix
    # (`Type535Enum`) that changes as the schema grows — and the generated frontend
    # SDK imports that name. Pinning it keeps the client's type stable.
    "ENUM_NAME_OVERRIDES": {
        "DocumentTypeEnum": "apps.diplomas.presentation.api.v1.diplomas.serializers.DOCUMENT_TYPES",
        # The award vocabulary appears under three field names — `award` on a protocol
        # row, `value` on a dropdown option, `award` on a public row — so it collides
        # with itself as well as with unrelated `value` fields elsewhere. Same reason as
        # above: an unpinned name gets a hash suffix that moves as the schema grows.
        "ProtocolStatusEnum": "apps.results.presentation.api.v1.serializers.PROTOCOL_STATUS_VALUES",
    },
}

# --- OpenAPI docs access (API-000 §26, see config/api_docs.py) ------------
API_DOCS_USER = settings.api_docs_user
API_DOCS_PASSWORD = settings.api_docs_password

SITE_GATE_USER = settings.site_gate_user
SITE_GATE_PASSWORD = settings.site_gate_password

# --- CORS (locked to known origins, API-000 §26) --------------------------
CORS_ALLOWED_ORIGINS = settings.cors_allowed_origins
CORS_ALLOW_CREDENTIALS = True
# The frontend transport tags requests with custom headers the browser must be
# told to allow, or it blocks the preflight: a correlation id on every request
# (X-Request-ID, API-000 §7) and an idempotency key on unsafe creates
# (Idempotency-Key, API-000 §19).
CORS_ALLOW_HEADERS = (*default_headers, "x-request-id", "idempotency-key")

# --- Email / SMTP (transactional mail, IDN-002) ---------------------------
# Driven by the typed EmailSettings group. Development points at the Mailhog
# SMTP sink (mailhog:1025, no TLS); production supplies a real provider.
EMAIL_BACKEND = settings.email.backend
EMAIL_HOST = settings.email.host
EMAIL_PORT = settings.email.port
EMAIL_HOST_USER = settings.email.host_user
EMAIL_HOST_PASSWORD = settings.email.host_password
EMAIL_USE_TLS = settings.email.use_tls
EMAIL_USE_SSL = settings.email.use_ssl
EMAIL_TIMEOUT = settings.email.timeout
DEFAULT_FROM_EMAIL = settings.email.default_from

# The mail provider's per-mailbox quotas (OPS-009). Enforced on the way out in
# ``apps.notifications``, because a message the provider refuses is one a participant
# never receives.
MAIL_RATE_LIMIT_PER_MINUTE = settings.email.rate_limit_per_minute
MAIL_MAX_RECIPIENTS = settings.email.max_recipients
MAIL_MAX_BYTES = settings.email.max_bytes

# The second mailbox, for notices produced in batches. Falls back to the first, so a
# single-mailbox deployment needs no configuration and behaves exactly as before.
MAIL_BULK_FROM = settings.email.bulk_from or settings.email.default_from

# Public base URL of the web client, used to build user-facing links the backend
# emails (email-verification link, IDN-002). No trailing slash.
FRONTEND_BASE_URL = settings.frontend_base_url.rstrip("/")

# Path to the built SPA shell Django serves for browser routes, with the head
# resolved server-side (see :mod:`config.spa`). Empty leaves it unrouted.
SPA_INDEX_PATH = settings.spa_index_path

# Base URL encoded into a diploma's QR code (``<base>/verify/<token>``). Defaults
# to the web client; DIPLOMA_VERIFICATION_BASE_URL overrides it when authenticity
# checks are served from a separate domain. Never hardcoded in the renderer.
DIPLOMA_VERIFICATION_BASE_URL = (settings.diploma_verification_base_url or settings.frontend_base_url).rstrip("/")

# Hours before an unpaid, submitted order (no payment receipt attached) is
# auto-cancelled. Configurable via APPLICATION_PAYMENT_WINDOW_HOURS (default 48).
APPLICATION_PAYMENT_WINDOW_HOURS = settings.application_payment_window_hours

# How long an order edited after submission must go quiet before the organizer is
# told what changed — the pause that folds one editing session into one letter.
# Configurable via APPLICATION_REVISION_QUIET_MINUTES (default 5).
APPLICATION_REVISION_QUIET_MINUTES = settings.application_revision_quiet_minutes

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

# Acknowledge a task when it *finishes*, not when it is picked up — and hand it back if the
# worker dies holding it.
#
# This is what a deploy depends on. Celery's default acknowledges on delivery, so the message is
# already gone from the broker while the work runs: a worker stopped mid-task (a rollout, an OOM
# kill, a lost machine) takes the task with it. Nothing errors and nothing retries — a print run
# that was most of the way through three thousand diplomas simply never finishes, and the only
# evidence is a job that stays unfinished forever.
#
# The cost of late acknowledgement is that a task can run twice: once interrupted, once
# redelivered. That is the right trade here because the long tasks are re-runnable by design —
# the unpaid-order sweep recomputes from the database each run (see CELERY_BEAT_SCHEDULE below),
# and print generation skips diplomas that already carry a rendered PDF unless asked to force
# them. A task that is *not* safe to run twice must say so itself; it cannot rely on the broker
# to guarantee it, because the broker never could.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Two mailboxes double the send rate, but on their own they do not fix ordering: with one
# queue a password reset still waits behind five hundred batch notices. Redis has no native
# priorities, so Celery emulates them with one list per step - which is why the steps have
# to be declared here for a priority to mean anything at all (OPS-009).
CELERY_TASK_DEFAULT_PRIORITY = 5
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "priority_steps": [0, 3, 6, 9],
    "sep": ":",
    "queue_order_strategy": "priority",
}

# Mail gets its own queue, and therefore its own worker (OPS-009 §"Throughput").
#
# Measured against the provider: a message costs ~2.8 s, nearly all of it opening an SSL
# connection and authenticating. One slot delivers ~21 messages a minute, so the allowance
# of 30 could never be reached - the bottleneck was our own reconnecting, not the quota.
# A worker at concurrency 4 clears it with room to spare and still uses only 4 of the 10
# sessions the contract permits per mailbox.
#
# The separation matters beyond throughput: on a shared queue a password reset waits behind
# whatever a print run is doing, and priorities cannot help across unrelated task types.
#
# **A worker must consume this queue or mail stops.** See the ``mail-worker`` service in
# docker-compose.yml, and OPS-008 §5 for a host deployment.
CELERY_TASK_ROUTES = {
    "notifications.deliver_email": {"queue": "mail"},
}

# One message reserved per slot, and this is what makes the priority above real.
#
# Celery applies priority when it *fetches* from the queue. At the default multiplier of 4
# a mail worker with four slots reserves sixteen messages up front - so a password reset
# queued behind a batch of receipts waits for all sixteen to go out, ~45 seconds at 2.8 s
# each, no matter what priority it carries. The priority would look configured and do
# almost nothing under exactly the load it exists for.
#
# With 1, at most four messages are in flight and every next fetch reconsults priority: a
# priority letter waits for one message, not sixteen. Prefetching buys pipelining for tasks
# measured in milliseconds; nothing here is one.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Periodic jobs. The unpaid-order sweep is durable: it recomputes overdue orders
# from the DB each run, so it survives web/worker/beat restarts (unlike per-order
# ETA jobs). Interval via APPLICATION_PAYMENT_SWEEP_MINUTES (default 15).
CELERY_BEAT_SCHEDULE = {
    "sweep-unpaid-applications": {
        "task": "applications.sweep_unpaid_applications",
        "schedule": settings.application_payment_sweep_minutes * 60.0,
    },
    # Durable in the same way: the journal in the database is the source of truth, so
    # a restart at any point loses no edit and re-sends none. Interval via
    # APPLICATION_REVISION_DIGEST_MINUTES (default 15).
    "notify-application-revisions": {
        "task": "applications.notify_application_revisions",
        "schedule": settings.application_revision_digest_minutes * 60.0,
    },
}

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
