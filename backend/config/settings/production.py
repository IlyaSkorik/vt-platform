"""Production settings.

Hardened environment (ARCH-001 §21). Secure defaults are enforced here; all
secrets and hosts arrive via environment variables through the typed settings
object — nothing sensitive is hard-coded.
"""

from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

# --- Refuse to boot on a development secret ---------------------------------
#
# `DJANGO_SECRET_KEY` has a default so the dev stack starts with no configuration at all
# (env.py). That default must never reach a deployment: it signs sessions, password-reset
# links and — per OPS-007 — decides where diploma files are written, so a known value is a
# full compromise of all three.
#
# `manage.py check --deploy` reports this, but a check nobody runs is not a control. Failing
# at import means a misconfigured container exits immediately and visibly instead of coming
# up and serving traffic that only looks fine.
#
# `collectstatic` runs in the image build, where no real secret exists or should. It sets a
# throwaway value, which passes: what is rejected is the *known* default, not any short key.
_INSECURE_SECRET_KEY = "insecure-dev-secret-key-change-me"

if SECRET_KEY == _INSECURE_SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is still the development default. Generate one per environment, "
        "e.g. `python -c 'import secrets; print(secrets.token_urlsafe(64))'`, and keep it in "
        "the secret store (OPS-008 §9) — rotating it invalidates sessions and password-reset "
        "links, and changes where new diploma files are written (OPS-007)."
    )

# ALLOWED_HOSTS defaults to ["localhost"], which in a deployment answers every real request
# with a 400. That is loud rather than dangerous, but it is a misconfiguration either way and
# cheaper to catch here than in the logs.
if not os.environ.get("DJANGO_ALLOWED_HOSTS"):
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS is unset. Set it to the deployment's hostname(s), comma-separated.")

# --- Transport & cookie security (ARCH-001 §21.2) -------------------------
SECURE_SSL_REDIRECT = True

# The liveness and readiness probes (ARCH-001 §17.4) are the one thing that must answer over
# plain HTTP. A container healthcheck and most load balancers probe the port directly, with no
# `X-Forwarded-Proto` to say otherwise — so `SECURE_SSL_REDIRECT` answers 301, the probe never
# sees a 200, and the container is marked unhealthy forever while the application is fine.
# (Worse, a client that follows the redirect then speaks TLS to a plain port and the server logs
# "Invalid HTTP request" instead of anything that points at the cause.)
#
# Exempting them is safe: both return a fixed JSON literal and read nothing.
SECURE_REDIRECT_EXEMPT = [r"^healthz$", r"^readyz$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

# --- Logging: put the traceback where the operator can read it --------------
#
# Django's built-in configuration filters its console handler behind
# `require_debug_true`, so with DEBUG off an unhandled exception reaches only
# `mail_admins` — and with no ADMINS configured, that means **nowhere**. A 500 then
# arrives at the browser with nothing behind it anywhere on the host, which is the
# worst possible shape for a failure that only happens in production (a bucket the
# credentials cannot write to, say).
#
# So the console handler comes back unconditionally and `django.request` is pinned
# to it. Everything in this stack logs to stdout and Docker collects it, which makes
# `docker compose logs backend` the one place to look.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # `propagate: False` so a 500 is logged once, not once here and again at root.
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Boto's own chatter is INFO-noisy and says nothing the request log does not.
        "botocore": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "boto3": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "s3transfer": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
