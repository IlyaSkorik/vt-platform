"""URL entry point for the Identity & Access bounded context.

Aggregates the context's versioned REST routes for mounting under the platform's
``/api/v1/`` prefix by ``config/urls.py`` (ARCH-001 §14, API-000 §2). Only the
authentication surface (API-001 §4.1-§4.6) is wired today; further resource
routers are added here as they are implemented.
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("apps.identity.presentation.api.v1.auth.urls")),
]
