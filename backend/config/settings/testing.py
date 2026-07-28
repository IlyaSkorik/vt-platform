"""Testing settings.

Fast, deterministic, and self-contained: domain/application unit tests run
without external services (ARCH-001 §28.2). An in-memory SQLite database keeps
``manage.py test`` and ``pytest`` runnable anywhere without a live PostgreSQL
instance; integration tests that require real PostgreSQL/Redis run against the
Docker services in CI using the base/production database configuration.
"""

from __future__ import annotations

from .base import *

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# In-memory broker so Celery tasks execute inline during tests.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Fast, insecure hasher — tests only.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# In-memory email backend so tests assert on ``django.core.mail.outbox`` without
# a live SMTP server (the SMTP→Mailhog path is exercised by the running stack). Delivery
# still goes through the Celery task, which runs inline here.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# The provider's per-minute allowance is off for the suite. The cache is shared across the
# whole run, so a real quota would start throttling whichever tests happened to land in a
# busy minute - and the limiter has its own tests that set the limit they need.
MAIL_RATE_LIMIT_PER_MINUTE = 0

# Whitenoise manifest storage requires collectstatic; use plain storage in tests.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
