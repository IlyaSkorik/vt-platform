"""Organizer routes for the Voting context (mounted under ``/api/v1/``)."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("apps.voting.presentation.api.v1.urls")),
]
