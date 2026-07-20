"""URL routes for Organization staff endpoints."""

from __future__ import annotations

from django.urls import path

from apps.organization.presentation.api.v1.staff.views import (
    StaffInvitationAcceptanceView,
    StaffInvitationCollectionView,
    StaffInvitationDetailView,
    StaffInvitationRevokeView,
    StaffMemberCollectionView,
    StaffMemberDetailView,
    StaffMemberRevokeView,
)

app_name = "organization_staff"

urlpatterns = [
    path("staff/invitations", StaffInvitationCollectionView.as_view(), name="invitations"),
    path("staff/invitations/accept", StaffInvitationAcceptanceView.as_view(), name="accept"),
    path(
        "staff/invitations/<uuid:invitation_id>/revoke",
        StaffInvitationRevokeView.as_view(),
        name="invitation-revoke",
    ),
    path("staff/invitations/<str:token>", StaffInvitationDetailView.as_view(), name="detail"),
    path("staff/members", StaffMemberCollectionView.as_view(), name="members"),
    path("staff/members/<uuid:membership_id>", StaffMemberDetailView.as_view(), name="member-detail"),
    path(
        "staff/members/<uuid:membership_id>/revoke",
        StaffMemberRevokeView.as_view(),
        name="member-revoke",
    ),
]
