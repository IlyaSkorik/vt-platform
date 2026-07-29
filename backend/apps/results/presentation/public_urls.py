"""URL router for the public Results surface (no authentication)."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [path("", include("apps.results.presentation.api.v1.public_urls"))]
