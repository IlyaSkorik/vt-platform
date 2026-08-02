"""URL entry point for the Identity & Access bounded context.

Aggregates the context's versioned REST routes for mounting under the platform's
``/api/v1/`` prefix by ``config/urls.py`` (ARCH-001 §14, API-000 §2). Two
surfaces are wired: authentication (API-001 §4.1-§4.6), and the account's own
self-service sub-resources under ``/users/me``. Further resource routers are
added here as they are implemented.
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("apps.identity.presentation.api.v1.auth.urls")),
    path("", include("apps.identity.presentation.api.v1.account.urls")),
]
