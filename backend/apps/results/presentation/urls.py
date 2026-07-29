"""URL router for the Results bounded context (organizer surface)."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [path("", include("apps.results.presentation.api.v1.urls"))]
