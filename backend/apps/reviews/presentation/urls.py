"""Organizer routes for the Reviews context (mounted under ``/api/v1/``)."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("apps.reviews.presentation.api.v1.urls")),
]
