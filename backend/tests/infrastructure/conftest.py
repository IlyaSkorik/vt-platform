"""Test configuration for the infrastructure (persistence-adapter) layer.

Infrastructure tests exercise the **real Django ORM against real PostgreSQL** —
no mocks, no in-memory substitute (ARCH-001 §28.2). The default ``testing``
settings use in-memory SQLite so the framework-free domain/application suites run
anywhere; the repository, by contrast, must be verified against the database it
actually targets, because its behaviour depends on PostgreSQL semantics — partial
unique constraints, ``UPDATE … RETURNING`` row counts for optimistic locking, and
real ``IntegrityError`` translation.

This conftest repoints Django's ``default`` database at the local PostgreSQL
service (the same instance ``docker-compose`` runs) before pytest-django builds
the test database. Only tests under ``tests/infrastructure/`` request a database,
so no other suite is affected. Connection parameters come from the environment
(the ``POSTGRES_*`` variables consumed by ``config.settings.env``) with the
project's development defaults.
"""

from __future__ import annotations

import os

from django.conf import settings

# Repoint the default connection at PostgreSQL. Executed at conftest import time —
# during collection, before pytest-django's session-scoped ``django_db_setup``
# creates the test database — so the test DB is created on PostgreSQL, not SQLite.
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
