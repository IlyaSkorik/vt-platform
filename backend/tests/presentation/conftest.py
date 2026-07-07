"""Test configuration for the presentation (REST edge) layer.

The authentication endpoints are integration-tested end to end — through DRF's
``APIClient`` against the **real database** (registration writes a user, login
reads it, refresh/logout write the SimpleJWT blacklist), so this suite runs on
real PostgreSQL rather than the default in-memory SQLite (ARCH-001 §28.2). This
conftest repoints Django's ``default`` connection at the local PostgreSQL service
before pytest-django builds the test database, mirroring
``tests/infrastructure/conftest.py``; connection parameters come from the
``POSTGRES_*`` environment variables with the project's development defaults.
"""

from __future__ import annotations

import os

from django.conf import settings

settings.DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("POSTGRES_DB", "vt_platform"),
    "USER": os.environ.get("POSTGRES_USER", "vt_platform"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "vt_platform"),
    "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
    "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    "ATOMIC_REQUESTS": False,
    "AUTOCOMMIT": True,
    "CONN_MAX_AGE": 0,
    "CONN_HEALTH_CHECKS": False,
    "OPTIONS": {},
    "TIME_ZONE": None,
    "TEST": {"NAME": "test_vt_platform_infra"},
}
