"""URL entry point for the Applications bounded context.

Aggregates the context's versioned REST routes for mounting under the platform's
``/api/v1/`` prefix by ``config/urls.py`` (ARCH-001 §14, API-000 §2).
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("apps.applications.presentation.api.v1.orders.urls")),
    path("", include("apps.applications.presentation.api.v1.submissions.urls")),
    path("", include("apps.applications.presentation.api.v1.organizer.urls")),
]
