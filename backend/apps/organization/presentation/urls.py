"""URL routes for the Organization bounded context."""

from __future__ import annotations

from django.urls import include, path

app_name = "organization"

urlpatterns = [
    path("", include("apps.organization.presentation.api.v1.staff.urls")),
]
