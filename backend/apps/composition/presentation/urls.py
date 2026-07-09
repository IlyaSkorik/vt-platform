"""URL entry point for the composition edge.

Aggregates the edge's versioned routes for mounting under ``/api/v1/`` by
``config/urls.py`` (ARCH-001 §14, API-000 §2).
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("apps.composition.presentation.api.v1.urls")),
]
