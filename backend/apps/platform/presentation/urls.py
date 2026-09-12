"""URL routes for the platform operator's console."""

from __future__ import annotations

from django.urls import path

from apps.platform.presentation.api.v1.views import (
    PlatformAudienceView,
    PlatformDashboardView,
    PlatformLoadTestView,
    PlatformOrganizationDetailView,
    PlatformOrganizationModulesView,
    PlatformOrganizationsView,
    PlatformPurgeSearchView,
    PlatformPurgeTargetView,
)

app_name = "platform"

urlpatterns = [
    path("platform/dashboard", PlatformDashboardView.as_view(), name="dashboard"),
    # Head counts of people rather than of work: read outside the dashboard so the
    # filters on that screen visibly do not apply to them.
    path("platform/audience", PlatformAudienceView.as_view(), name="audience"),
    path("platform/organizations", PlatformOrganizationsView.as_view(), name="organizations"),
    path("platform/organizations/<str:organization_id>", PlatformOrganizationDetailView.as_view(), name="organization-detail"),
    # Which parts of the platform this organization was sold. Its own route rather
    # than a field on the terms PATCH: a different screen, a different decision.
    path("platform/organizations/<str:organization_id>/modules", PlatformOrganizationModulesView.as_view(), name="organization-modules"),
    # The operator's own test bench: seed a synthetic festival, run generation on it
    # for real, and remove every trace afterwards.
    path("platform/loadtest/diplomas", PlatformLoadTestView.as_view(), name="loadtest-diplomas"),
    # The eraser. `search` is listed before the `{target}/{objectId}` pattern so the
    # literal route wins — otherwise a search would be read as an object named "search".
    path("platform/purge/search", PlatformPurgeSearchView.as_view(), name="purge-search"),
    path("platform/purge/<str:target>/<str:object_id>", PlatformPurgeTargetView.as_view(), name="purge-target"),
]
