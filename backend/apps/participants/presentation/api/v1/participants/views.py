"""Participant controllers for the Participants REST API v1.

Noun-resource endpoints — the participant collection/detail, the guardian-link
sub-collection and its verification, and the verify/activate lifecycle transitions
modelled as sub-resources (API-000 §3.3) — each a thin HTTP adapter that follows
one flow:

    HTTP request → serializer (validate) → command → handler → DTO → HTTP response

A view never queries the ORM, applies a business rule, or holds domain logic: it
validates the request shape, maps it onto an application command/query, invokes a
handler assembled by the :mod:`composition` root, and renders the resulting DTO
into the API envelope (API-000 §7) or an RFC 9457 problem (API-000 §8, via
:mod:`apps.participants.presentation.api.v1.problems`).

Endpoints are authenticated (deny-by-default, ARCH-001 §12.4): the acting adult is
the JWT subject, recorded as the participant's creator (IDN-004 — children never
hold accounts). Fine-grained guardian/teacher scoping (PRT-003, PRT-004) layers on
top in a later revision.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from apps.participants.application.commands import (
    ActivateParticipantCommand,
    CreateParticipantCommand,
    ProposeGuardianLinkCommand,
    VerifyGuardianLinkCommand,
    VerifyParticipantCommand,
)
from apps.participants.application.dto import ParticipantDto
from apps.participants.application.exceptions import ApplicationError
from apps.participants.application.queries import GetParticipantQuery
from apps.participants.presentation.api.v1 import problems
from apps.participants.presentation.api.v1.participants import composition
from apps.participants.presentation.api.v1.participants.serializers import (
    CreateParticipantRequestSerializer,
    ParticipantResponseSerializer,
    ProblemDetailSerializer,
    ProposeGuardianLinkRequestSerializer,
)

_TAG = "Participants"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _iso(value: Any) -> Any:
    """Render a datetime as a ``Z``-suffixed ISO-8601 string, passing ``None`` through."""
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _participant_resource(dto: ParticipantDto) -> dict[str, Any]:
    """Project a :class:`ParticipantDto` into the participant resource (DIA-001 §4.2)."""
    return {
        "id": dto.id,
        "type": "participant",
        "displayAlias": dto.display_alias,
        "displayName": dto.full_name,
        "status": dto.status,
        "dateOfBirth": dto.date_of_birth,
        "guardianLinks": [
            {
                "guardianId": link.guardian_id,
                "relationshipType": link.relationship_type,
                "status": link.status,
                "establishedAt": _iso(link.established_at),
            }
            for link in dto.guardian_links
        ],
        "institutionId": dto.institution_id,
        "consentRecorded": dto.consent_id is not None,
        "createdAt": _iso(dto.created_at),
        "updatedAt": _iso(dto.updated_at),
    }


def _envelope(request: Request, data: dict[str, Any], *, status: int) -> Response:
    """Wrap a resource in the ``data``/``meta`` envelope (API-000 §7.1)."""
    correlation_id = problems.request_id(request)
    return Response(
        {"data": data, "meta": {"requestId": correlation_id}},
        status=status,
        headers={"X-Request-ID": correlation_id},
    )


def _optional_str(value: object) -> str | None:
    """Coerce an optional serializer value to ``str | None`` (blank → ``None``)."""
    if value is None:
        return None
    text = str(value)
    return text if text else None


class _AuthenticatedView(APIView):
    """Base for the participant endpoints: stateless JWT auth, deny-by-default."""

    authentication_classes = (JWTStatelessUserAuthentication,)
    permission_classes = (IsAuthenticated,)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


class ParticipantCollectionView(_AuthenticatedView):
    """POST /api/v1/participants — register a new participant (DATA-004 §4.3)."""

    @extend_schema(
        tags=[_TAG],
        operation_id="participants_create",
        summary="Register a participant",
        description="Create a new participant under the authenticated guardian/teacher.",
        request=CreateParticipantRequestSerializer,
        responses={
            201: ParticipantResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Display alias in use."),
            422: OpenApiResponse(ProblemDetailSerializer, description="Alias reveals identity."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = CreateParticipantRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(
                serializer.errors, instance=instance, request=request
            )
        data = serializer.validated_data
        command = CreateParticipantCommand(
            first_name=str(data["firstName"]),
            last_name=str(data["lastName"]),
            middle_name=_optional_str(data.get("middleName")),
            date_of_birth=str(data["dateOfBirth"]),
            display_alias=str(data["displayAlias"]),
            created_by_id=str(request.user.id),
            created_by_type=str(data["createdByType"]),
        )
        try:
            result = composition.build_create_participant_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        response = _envelope(request, _participant_resource(result.participant), status=201)
        response["Location"] = f"/api/v1/participants/{result.participant.id}"
        return response


class ParticipantDetailView(_AuthenticatedView):
    """GET /api/v1/participants/{id} — retrieve a participant."""

    @extend_schema(
        tags=[_TAG],
        operation_id="participants_retrieve",
        summary="Retrieve a participant",
        request=None,
        responses={
            200: ParticipantResponseSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
        },
    )
    def get(self, request: Request, participant_id: str) -> Response:
        instance = request.path
        try:
            dto = composition.build_get_participant_handler().handle(
                GetParticipantQuery(participant_id=participant_id)
            )
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _participant_resource(dto), status=200)


class GuardianLinkCollectionView(_AuthenticatedView):
    """POST /api/v1/participants/{id}/guardian-links — propose a guardian relationship."""

    @extend_schema(
        tags=[_TAG],
        operation_id="participants_guardian_link_create",
        summary="Propose a guardian link",
        request=ProposeGuardianLinkRequestSerializer,
        responses={
            201: ParticipantResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Guardian already linked."),
        },
    )
    def post(self, request: Request, participant_id: str) -> Response:
        instance = request.path
        serializer = ProposeGuardianLinkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(
                serializer.errors, instance=instance, request=request
            )
        data = serializer.validated_data
        command = ProposeGuardianLinkCommand(
            participant_id=participant_id,
            guardian_id=str(data["guardianId"]),
            relationship_type=str(data["relationshipType"]),
        )
        try:
            result = composition.build_propose_guardian_link_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _participant_resource(result.participant), status=201)


class GuardianLinkVerificationView(_AuthenticatedView):
    """POST /api/v1/participants/{id}/guardian-links/{guardianId}/verification."""

    @extend_schema(
        tags=[_TAG],
        operation_id="participants_guardian_link_verify",
        summary="Verify a guardian link",
        request=None,
        responses={
            200: ParticipantResponseSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Link not pending."),
        },
    )
    def post(self, request: Request, participant_id: str, guardian_id: str) -> Response:
        instance = request.path
        command = VerifyGuardianLinkCommand(
            participant_id=participant_id, guardian_id=guardian_id
        )
        try:
            result = composition.build_verify_guardian_link_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _participant_resource(result.participant), status=200)


class ParticipantVerificationView(_AuthenticatedView):
    """POST /api/v1/participants/{id}/verification — verify a participant's details."""

    @extend_schema(
        tags=[_TAG],
        operation_id="participants_verify",
        summary="Verify a participant",
        request=None,
        responses={
            200: ParticipantResponseSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Invalid transition."),
        },
    )
    def post(self, request: Request, participant_id: str) -> Response:
        instance = request.path
        command = VerifyParticipantCommand(participant_id=participant_id)
        try:
            result = composition.build_verify_participant_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _participant_resource(result.participant), status=200)


class ParticipantActivationView(_AuthenticatedView):
    """POST /api/v1/participants/{id}/activation — activate a participant (PRT-001)."""

    @extend_schema(
        tags=[_TAG],
        operation_id="participants_activate",
        summary="Activate a participant",
        request=None,
        responses={
            200: ParticipantResponseSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Invalid transition."),
            422: OpenApiResponse(ProblemDetailSerializer, description="Activation blocked."),
        },
    )
    def post(self, request: Request, participant_id: str) -> Response:
        instance = request.path
        command = ActivateParticipantCommand(participant_id=participant_id)
        try:
            result = composition.build_activate_participant_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _participant_resource(result.participant), status=200)
