"""REST views for Organization staff invitation endpoints."""
from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from apps.identity.presentation.api.v1.problems import (
    problem_response,
    request_id,
    validation_problem,
)
from apps.organization.application.dto.commands import (
    AcceptStaffInvitationCommand,
    InviteStaffCommand,
)
from apps.organization.application.dto.queries import GetStaffInvitationQuery
from apps.organization.application.exceptions import ApplicationError
from apps.organization.composition import (
    build_accept_staff_invitation_handler,
    build_get_staff_invitation_handler,
    build_invite_staff_handler,
)
from apps.organization.presentation.api.v1.staff.serializers import (
    AcceptInvitationRequestSerializer,
    InvitationResponseSerializer,
    InviteStaffRequestSerializer,
    MembershipResponseSerializer,
    ProblemDetailSerializer,
    StaffInvitationDetailSerializer,
)

_TAG = "Organization"

_PROBLEM_MAP = {
    "organization_not_found": (404, "not-found", "Resource not found", None),
    "staff_invitation_not_found": (404, "not-found", "Resource not found", None),
    "invalid_input": (400, "validation-error", "Validation failed", None),
    "invalid_invitation_token": (410, "token-expired", "Invitation token expired", None),
    "user_already_staff": (409, "conflict", "Conflict", None),
    "permission_denied": (403, "forbidden", "Forbidden", None),
    "invitation_conflict": (409, "conflict", "Conflict", None),
    "invitation_state_conflict": (409, "conflict", "Conflict", None),
}


def application_problem(exc: ApplicationError, *, instance: str, request: Request) -> Response:
    status, type_suffix, title, code = _PROBLEM_MAP.get(
        exc.code, (400, "bad-request", "Bad request", None)
    )
    return problem_response(
        status=status,
        type_suffix=type_suffix,
        title=title,
        detail=str(exc) or title,
        instance=instance,
        correlation_id=request_id(request),
        code=code,
    )

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
    """POST /api/v1/staff/invitations — create a staff invitation."""

    authentication_classes = (JWTStatelessUserAuthentication,)
    permission_classes = (IsAuthenticated,)

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
            "data": {
                "id": result.invitation.id,
                "organizationId": result.invitation.organization_id,
                "email": result.invitation.email,
                "role": result.invitation.role,
                "expiresAt": result.invitation.expires_at,
                "invitedBy": result.invitation.invited_by,
                "acceptedAt": result.invitation.accepted_at,
                "revokedAt": result.invitation.revoked_at,
                "createdAt": result.invitation.created_at,
            },
            "meta": {"requestId": request_id(request)},
        }
        return Response(body, status=201)


class StaffInvitationAcceptanceView(APIView):
    """POST /api/v1/staff/invitations/accept — accept a staff invitation."""

    authentication_classes = (JWTStatelessUserAuthentication,)
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

        data = serializer.validated_data
        command = AcceptStaffInvitationCommand(
            raw_token=str(data["token"]),
            accepted_by=str(request.user.id),
            email=str(request.user.email),
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
