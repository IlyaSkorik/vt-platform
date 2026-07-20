"""Serializers for the Organization staff endpoints."""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

__all__ = [
    "ChangeStaffRoleRequestSerializer",
    "InvitationListResponseSerializer",
    "InvitationResponseSerializer",
    "InviteStaffRequestSerializer",
    "MembershipResponseSerializer",
    "ProblemDetailSerializer",
    "StaffInvitationDetailSerializer",
    "StaffMemberListResponseSerializer",
]

_ROLE_CHOICES = [
    "OWNER",
    "DIRECTOR",
    "FINANCE",
    "COMPETITION_MANAGER",
    "CONTENT_MANAGER",
    "MODERATOR",
    "SUPPORT",
]


class InviteStaffRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a staff-invitation creation request."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=_ROLE_CHOICES)


class ChangeStaffRoleRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate a staff-role-change request."""

    role = serializers.ChoiceField(choices=_ROLE_CHOICES)


class AcceptInvitationRequestSerializer(serializers.Serializer[dict[str, object]]):
    """Validate an invitation-acceptance request."""

    token = serializers.CharField()


class MetaSerializer(serializers.Serializer[dict[str, object]]):
    """The meta envelope block."""

    requestId = serializers.CharField()


class InvitationResourceSerializer(serializers.Serializer[dict[str, object]]):
    """Serialize an invitation resource."""

    id = serializers.UUIDField()
    organizationId = serializers.UUIDField(source="organization_id")
    email = serializers.EmailField()
    role = serializers.CharField()
    status = serializers.CharField()
    expiresAt = serializers.DateTimeField(source="expires_at")
    invitedBy = serializers.UUIDField(source="invited_by")
    acceptedAt = serializers.DateTimeField(source="accepted_at", allow_null=True)
    revokedAt = serializers.DateTimeField(source="revoked_at", allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at")


class MembershipResourceSerializer(serializers.Serializer[dict[str, object]]):
    """Serialize an accepted-membership resource."""

    role = serializers.CharField()
    status = serializers.CharField()
    organizationId = serializers.UUIDField(source="organization_id")


class StaffMemberResourceSerializer(serializers.Serializer[dict[str, object]]):
    """Serialize a staff-member resource (membership joined to its user card)."""

    id = serializers.UUIDField()
    userId = serializers.UUIDField(source="user_id")
    email = serializers.EmailField(allow_null=True)
    displayName = serializers.CharField(source="display_name", allow_null=True)
    role = serializers.CharField()
    status = serializers.CharField()
    invitedAt = serializers.DateTimeField(source="invited_at", allow_null=True)
    acceptedAt = serializers.DateTimeField(source="accepted_at", allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at")


class StaffInvitationDetailSerializer(serializers.Serializer[dict[str, object]]):
    """Serialize an invitation-detail resource."""

    organizationName = serializers.CharField(source="organization_name")
    role = serializers.CharField()
    expiresAt = serializers.DateTimeField(source="expires_at")
    invitedEmail = serializers.EmailField(source="invited_email")


InvitationResponseSerializer = inline_serializer(
    name="InvitationResponse",
    fields={"data": InvitationResourceSerializer(), "meta": MetaSerializer()},
)

InvitationListResponseSerializer = inline_serializer(
    name="InvitationListResponse",
    fields={"data": InvitationResourceSerializer(many=True), "meta": MetaSerializer()},
)

MembershipResponseSerializer = inline_serializer(
    name="MembershipResponse",
    fields={"data": MembershipResourceSerializer(), "meta": MetaSerializer()},
)

StaffMemberListResponseSerializer = inline_serializer(
    name="StaffMemberListResponse",
    fields={"data": StaffMemberResourceSerializer(many=True), "meta": MetaSerializer()},
)

ProblemDetailSerializer = inline_serializer(
    name="ProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
        "code": serializers.CharField(required=False),
    },
)
