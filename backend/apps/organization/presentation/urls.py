"""URL routes for the Organization bounded context."""

from __future__ import annotations

from django.urls import include, path

from apps.organization.presentation.api.v1.profile_views import OrganizationProfileView

app_name = "organization"

urlpatterns = [
    path("organization/profile", OrganizationProfileView.as_view(), name="profile"),
    path("", include("apps.organization.presentation.api.v1.staff.urls")),
]
