"""ASGI entry point.

The platform serves under ASGI (Uvicorn workers under Gunicorn) for async and
future WebSocket readiness (ARCH-001 §6.1).
"""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_asgi_application()
