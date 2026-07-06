"""Development settings.

Local, Docker-Compose-oriented environment (ARCH-001 §16.1, §17.3). Debug is
enabled and hosts are permissive; all other values come from the typed
settings object and local ``.env``.
"""

from __future__ import annotations

from .base import *
from .base import INSTALLED_APPS, settings

DEBUG = True

ALLOWED_HOSTS = settings.allowed_hosts or ["*"]

# Browsable API convenience during development.
INSTALLED_APPS = [*INSTALLED_APPS]

# Relaxed CORS for local frontends is still origin-scoped in .env.
CORS_ALLOW_ALL_ORIGINS = False
