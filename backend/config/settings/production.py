"""Production settings.

Hardened environment (ARCH-001 §21). Secure defaults are enforced here; all
secrets and hosts arrive via environment variables through the typed settings
object — nothing sensitive is hard-coded.
"""

from __future__ import annotations

from .base import *

DEBUG = False

# --- Transport & cookie security (ARCH-001 §21.2) -------------------------
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
