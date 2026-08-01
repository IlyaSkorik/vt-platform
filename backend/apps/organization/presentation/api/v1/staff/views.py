"""REST views for Organization staff invitation endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth.models import AnonymousUser
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.composition import build_user_directory
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.identity.presentation.api.v1.problems import (
    problem_response,
    request_id,
    validation_problem,
)
from apps.organization.application.dto.commands import (
    AcceptStaffInvitationCommand,
    ChangeStaffRoleCommand,
    InviteStaffCommand,
    RevokeStaffInvitationCommand,
    RevokeStaffMembershipCommand,
)
from apps.organization.application.dto.queries import (
    GetStaffInvitationQuery,
    ListStaffInvitationsQuery,
    ListStaffMembersQuery,
)
from apps.organization.application.exceptions import ApplicationError, PermissionDeniedError
from apps.organization.composition import (
    build_accept_staff_invitation_handler,
    build_change_staff_role_handler,
    build_get_staff_invitation_handler,
    build_invite_staff_handler,
    build_list_staff_invitations_handler,
    build_list_staff_members_handler,
    build_revoke_staff_invitation_handler,
    build_revoke_staff_membership_handler,
)
from apps.organization.presentation.api.v1.staff.serializers import (
    AcceptInvitationRequestSerializer,
    ChangeStaffRoleRequestSerializer,
    InvitationListResponseSerializer,
    InvitationResponseSerializer,
    InviteStaffRequestSerializer,
    MembershipResponseSerializer,
    ProblemDetailSerializer,
    StaffInvitationDetailSerializer,
    StaffMemberListResponseSerializer,
)
from apps.organization.presentation.permissions import IsOrganizationAdmin, IsOrganizationStaff

_TAG = "Organization"

_PROBLEM_MAP = {
    "organization_not_found": (404, "not-found", "Resource not found", None),
    "staff_invitation_not_found": (404, "not-found", "Resource not found", None),
    "staff_membership_not_found": (404, "not-found", "Resource not found", None),
    "invalid_input": (400, "validation-error", "Validation failed", None),
    "invalid_invitation_token": (410, "token-expired", "Invitation token expired", None),
    "user_already_staff": (409, "conflict", "Conflict", None),
    "permission_denied": (403, "forbidden", "Forbidden", None),
    "invitation_conflict": (409, "conflict", "Conflict", None),
    "organization_conflict": (409, "conflict", "Conflict", None),
    "organization_state_conflict": (409, "conflict", "Conflict", None),
    "invitation_state_conflict": (409, "conflict", "Conflict", None),
    "membership_state_conflict": (409, "conflict", "Conflict", None),
    "last_owner": (409, "conflict", "Conflict", None),
}


def application_problem(exc: ApplicationError, *, instance: str, request: Request) -> Response:
    status, type_suffix, title, code = _PROBLEM_MAP.get(exc.code, (400, "bad-request", "Bad request", None))
    return problem_response(
        status=status,
        type_suffix=type_suffix,
        title=title,
        detail=str(exc) or title,
        instance=instance,
        correlation_id=request_id(request),
        code=code,
    )


def _invitation_data(invitation: object) -> dict[str, object]:
    """Project an :class:`InvitationView` into its camelCase wire resource."""
    inv: Any = invitation
    return {
        "id": inv.id,
        "organizationId": inv.organization_id,
        "email": inv.email,
        "role": inv.role,
        "status": inv.status,
        "expiresAt": inv.expires_at,
        "invitedBy": inv.invited_by,
        "acceptedAt": inv.accepted_at,
        "revokedAt": inv.revoked_at,
        "createdAt": inv.created_at,
    }


def _member_data(member: object) -> dict[str, object]:
    """Project a :class:`StaffMemberView` into its camelCase wire resource."""
    m: Any = member
    return {
        "id": m.id,
        "userId": m.user_id,
        "email": m.email,
        "displayName": m.display_name,
        "role": m.role,
        "status": m.status,
        "invitedAt": m.invited_at,
        "acceptedAt": m.accepted_at,
        "createdAt": m.created_at,
    }


class StaffInvitationDetailView(APIView):
    """GET /api/v1/staff/invitations/{token} — look up a staff invitation."""

    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        tags=[_TAG],
        operation_id="getStaffInvitation",
        summary="Look up a staff invitation",
        description="Look up an invitation using the token from the email link.",
        responses={
            200: StaffInvitationDetailSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Invitation not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Invitation already accepted."),
            410: OpenApiResponse(ProblemDetailSerializer, description="Invitation expired."),
        },
    )
    def get(self, request: Request, token: str) -> Response:
        query = GetStaffInvitationQuery(raw_token=token)
        try:
            result = build_get_staff_invitation_handler().handle(query)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        serializer = StaffInvitationDetailSerializer(
            instance={
                "organization_name": result.organization_name,
                "role": result.role,
                "expires_at": result.expires_at,
                "invited_email": result.invited_email,
            }
        )
        return Response(serializer.data, status=200)


class StaffInvitationCollectionView(APIView):
    """GET/POST /api/v1/staff/invitations — list or create staff invitations.

    Reading the roster is open to any active staff member; creating an invitation
    is restricted to owners/directors (:class:`IsOrganizationAdmin`).
    """

    authentication_classes = (CredentialAwareJWTAuthentication,)

    def get_permissions(self) -> list[BasePermission]:
        gate = IsOrganizationStaff if self.request.method == "GET" else IsOrganizationAdmin
        return [IsAuthenticated(), gate()]

    @extend_schema(
        tags=[_TAG],
        operation_id="listStaffInvitations",
        summary="List staff invitations",
        description="List every invitation of the organization with its lifecycle status.",
        responses={
            200: InvitationListResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Organization not seeded."),
        },
    )
    def get(self, request: Request) -> Response:
        try:
            invitations = build_list_staff_invitations_handler().handle(ListStaffInvitationsQuery(requested_by=str(request.user.id)))
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        body = {
            "data": [_invitation_data(invitation) for invitation in invitations],
            "meta": {"requestId": request_id(request)},
        }
        return Response(body, status=200)

    @extend_schema(
        tags=[_TAG],
        operation_id="createStaffInvitation",
        summary="Invite a person to become staff",
        description="Create an invitation for a person to join the organization as staff.",
        request=InviteStaffRequestSerializer,
        responses={
            201: InvitationResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Forbidden."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Invitation conflict."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = InviteStaffRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=request.path, request=request)

        data = serializer.validated_data
        command = InviteStaffCommand(
            email=str(data["email"]),
            role=str(data["role"]),
            invited_by=str(request.user.id),
        )
        try:
            result = build_invite_staff_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        body = {
            "data": _invitation_data(result.invitation),
            "meta": {"requestId": request_id(request)},
        }
        return Response(body, status=201)


class StaffInvitationAcceptanceView(APIView):
    """POST /api/v1/staff/invitations/accept — accept a staff invitation."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=[_TAG],
        operation_id="acceptStaffInvitation",
        summary="Accept a staff invitation",
        description="Accept an invitation using the token from the email link.",
        request=AcceptInvitationRequestSerializer,
        responses={
            200: MembershipResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Forbidden or wrong invitee."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Invitation not found."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = AcceptInvitationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=request.path, request=request)

        if isinstance(request.user, AnonymousUser):
            return application_problem(
                ApplicationError("Authentication required."),
                instance=request.path,
                request=request,
            )

        # The stateless JWT carries only the subject id, not the email — resolve
        # the accepting user's email from Identity so the handler can verify the
        # invitation belongs to this person.
        try:
            user_uuid = uuid.UUID(str(request.user.id))
        except (ValueError, TypeError):
            return application_problem(
                PermissionDeniedError("The authenticated user is invalid."),
                instance=request.path,
                request=request,
            )
        card = build_user_directory().resolve({user_uuid}).get(user_uuid)
        if card is None:
            return application_problem(
                PermissionDeniedError("The authenticated user account was not found."),
                instance=request.path,
                request=request,
            )

        data = serializer.validated_data
        command = AcceptStaffInvitationCommand(
            raw_token=str(data["token"]),
            accepted_by=str(request.user.id),
            email=card.email,
        )
        try:
            result = build_accept_staff_invitation_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        body = {
            "data": {
                "role": result.membership.role,
                "status": result.membership.status,
                "organizationId": result.membership.organization_id,
            },
            "meta": {"requestId": request_id(request)},
        }
        return Response(body, status=200)


class StaffInvitationRevokeView(APIView):
    """POST /api/v1/staff/invitations/{invitation_id}/revoke — revoke an invitation."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationAdmin)

    @extend_schema(
        tags=[_TAG],
        operation_id="revokeStaffInvitation",
        summary="Revoke a staff invitation",
        description="Revoke a still-pending staff invitation before it is accepted.",
        request=None,
        responses={
            200: InvitationResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Invitation not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Invitation already accepted/revoked."),
        },
    )
    def post(self, request: Request, invitation_id: str) -> Response:
        command = RevokeStaffInvitationCommand(
            invitation_id=str(invitation_id),
            revoked_by=str(request.user.id),
        )
        try:
            invitation = build_revoke_staff_invitation_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        body = {"data": _invitation_data(invitation), "meta": {"requestId": request_id(request)}}
        return Response(body, status=200)


class StaffMemberCollectionView(APIView):
    """GET /api/v1/staff/members — list the organization's staff roster."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)

    @extend_schema(
        tags=[_TAG],
        operation_id="listStaffMembers",
        summary="List staff members",
        description="List every staff member with their role, status and Identity user card.",
        responses={
            200: StaffMemberListResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Organization not seeded."),
        },
    )
    def get(self, request: Request) -> Response:
        try:
            members = build_list_staff_members_handler().handle(ListStaffMembersQuery(requested_by=str(request.user.id)))
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        body = {
            "data": [_member_data(member) for member in members],
            "meta": {"requestId": request_id(request)},
        }
        return Response(body, status=200)


class StaffMemberDetailView(APIView):
    """PATCH /api/v1/staff/members/{membership_id} — change a member's role."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationAdmin)

    @extend_schema(
        tags=[_TAG],
        operation_id="changeStaffRole",
        summary="Change a staff member's role",
        description="Change the role of an active staff membership. The last active owner cannot be demoted.",
        request=ChangeStaffRoleRequestSerializer,
        responses={
            200: MembershipResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Membership not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Last owner or invalid state."),
        },
    )
    def patch(self, request: Request, membership_id: str) -> Response:
        serializer = ChangeStaffRoleRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_problem(serializer.errors, instance=request.path, request=request)

        command = ChangeStaffRoleCommand(
            membership_id=str(membership_id),
            new_role=str(serializer.validated_data["role"]),
            changed_by=str(request.user.id),
        )
        try:
            membership = build_change_staff_role_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        body = {
            "data": {
                "role": membership.role,
                "status": membership.status,
                "organizationId": membership.organization_id,
            },
            "meta": {"requestId": request_id(request)},
        }
        return Response(body, status=200)


class StaffMemberRevokeView(APIView):
    """POST /api/v1/staff/members/{membership_id}/revoke — revoke staff access."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationAdmin)

    @extend_schema(
        tags=[_TAG],
        operation_id="revokeStaffMembership",
        summary="Revoke a staff member's access",
        description="Revoke an active staff membership. The last active owner cannot be revoked.",
        request=None,
        responses={
            200: MembershipResponseSerializer,
            403: OpenApiResponse(ProblemDetailSerializer, description="Not organization staff."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Membership not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Last owner or already revoked."),
        },
    )
    def post(self, request: Request, membership_id: str) -> Response:
        command = RevokeStaffMembershipCommand(
            membership_id=str(membership_id),
            revoked_by=str(request.user.id),
        )
        try:
            membership = build_revoke_staff_membership_handler().handle(command)
        except ApplicationError as exc:
            return application_problem(exc, instance=request.path, request=request)

        body = {
            "data": {
                "role": membership.role,
                "status": membership.status,
                "organizationId": membership.organization_id,
            },
            "meta": {"requestId": request_id(request)},
        }
        return Response(body, status=200)
