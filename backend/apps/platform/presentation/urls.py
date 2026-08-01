"""URL routes for the platform operator's console."""

from __future__ import annotations

from django.urls import path

from apps.platform.presentation.api.v1.views import (
    PlatformDashboardView,
    PlatformOrganizationDetailView,
    PlatformOrganizationsView,
)

app_name = "platform"

urlpatterns = [
    path("platform/dashboard", PlatformDashboardView.as_view(), name="dashboard"),
    path("platform/organizations", PlatformOrganizationsView.as_view(), name="organizations"),
    path("platform/organizations/<str:organization_id>", PlatformOrganizationDetailView.as_view(), name="organization-detail"),
]
