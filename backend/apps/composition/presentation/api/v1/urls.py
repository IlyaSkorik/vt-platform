"""URL routes for the composition edge (mounted under ``/api/v1/``)."""

from __future__ import annotations

from django.urls import path

from apps.composition.presentation.api.v1.views import CurrentUserView

app_name = "composition"

urlpatterns = [
    path("users/me", CurrentUserView.as_view(), name="users-me"),
]
