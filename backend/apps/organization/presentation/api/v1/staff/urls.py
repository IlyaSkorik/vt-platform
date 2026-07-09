"""URL routes for Organization staff endpoints."""

from __future__ import annotations

from django.urls import path

from apps.organization.presentation.api.v1.staff.views import (
    StaffInvitationAcceptanceView,
    StaffInvitationCollectionView,
    StaffInvitationDetailView,
)

app_name = "organization_staff"

urlpatterns = [
    path("staff/invitations", StaffInvitationCollectionView.as_view(), name="invitations"),
    path("staff/invitations/accept", StaffInvitationAcceptanceView.as_view(), name="accept"),
    path("staff/invitations/<str:token>", StaffInvitationDetailView.as_view(), name="detail"),
]
