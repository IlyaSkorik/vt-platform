"""Teacher directory controllers for the Teacher Directory REST API v1.

Noun-resource endpoints - the teacher collection/detail plus archival/reactivation
modelled as sub-resources (API-000 §3.3) - each a thin HTTP adapter that follows one
flow:

    HTTP request -> serializer (validate) -> command -> handler -> DTO -> HTTP response

A view never queries the ORM, applies a business rule, or holds domain logic. Every
endpoint is authenticated (deny-by-default, ARCH-001 §12.4): the acting user is the
JWT subject and owns the directory being read or modified.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.teachers.application.commands import (
    AddTeacherCommand,
    ArchiveTeacherCommand,
    ReactivateTeacherCommand,
    UpdateTeacherCommand,
)
from apps.teachers.application.dto import TeacherDto
from apps.teachers.application.exceptions import ApplicationError
from apps.teachers.application.queries import GetTeacherDirectoryQuery, GetTeacherQuery
from apps.teachers.presentation.api.v1 import problems
from apps.teachers.presentation.api.v1.teachers import composition
from apps.teachers.presentation.api.v1.teachers.serializers import (
    AddTeacherRequestSerializer,
    ProblemDetailSerializer,
    TeacherDirectoryResponseSerializer,
    TeacherResponseSerializer,
    UpdateTeacherRequestSerializer,
)

_TAG = "Teacher Directory"


def _iso(value: Any) -> Any:
    """Render a datetime as a ``Z``-suffixed ISO-8601 string, passing ``None`` through."""
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _optional_str(value: object) -> str | None:
    """Coerce an optional serializer value to ``str | None`` (blank -> ``None``)."""
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _teacher_resource(dto: TeacherDto) -> dict[str, Any]:
    """Project a :class:`TeacherDto` into the teacher resource."""
    return {
        "id": dto.id,
        "type": "teacher",
        "ownerId": dto.owner_id,
        "firstName": dto.first_name,
        "lastName": dto.last_name,
        "middleName": dto.middle_name,
        "displayName": dto.full_name,
        "role": dto.role,
        "email": dto.email,
        "phone": dto.phone,
        "consentRecorded": dto.consent_recorded,
        "consentVersion": dto.consent_version,
        "status": dto.status,
        "archivedAt": _iso(dto.archived_at),
        "createdAt": _iso(dto.created_at),
        "updatedAt": _iso(dto.updated_at),
    }


def _envelope(request: Request, data: Any, *, status: int) -> Response:
    """Wrap a resource (or list) in the ``data``/``meta`` envelope (API-000 §7.1)."""
    correlation_id = problems.request_id(request)
    return Response(
        {"data": data, "meta": {"requestId": correlation_id}},
        status=status,
        headers={"X-Request-ID": correlation_id},
    )


class _AuthenticatedView(APIView):
    """Base for the teacher endpoints: stateless JWT auth, deny-by-default."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)


class TeacherCollectionView(_AuthenticatedView):
    """GET/POST /api/v1/teachers - list the directory or add a teacher."""

    @extend_schema(
        tags=[_TAG],
        operation_id="teachers_list",
        summary="List the personal teacher directory",
        parameters=[OpenApiParameter(name="includeArchived", type=bool, required=False, description="Include archived teachers.")],
        request=None,
        responses={200: TeacherDirectoryResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        instance = request.path
        include_archived = str(request.query_params.get("includeArchived", "")).lower() in {"1", "true", "yes"}
        query = GetTeacherDirectoryQuery(requested_by=str(request.user.id), include_archived=include_archived)
        try:
            entries = composition.build_get_teacher_directory_handler().handle(query)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, [_teacher_resource(dto) for dto in entries], status=200)

    @extend_schema(
        tags=[_TAG],
        operation_id="teachers_create",
        summary="Add a teacher to the directory",
        request=AddTeacherRequestSerializer,
        responses={
            201: TeacherResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
        },
    )
    def post(self, request: Request) -> Response:
        instance = request.path
        serializer = AddTeacherRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=instance, request=request)
        data = serializer.validated_data
        command = AddTeacherCommand(
            requested_by=str(request.user.id),
            first_name=str(data["firstName"]),
            last_name=str(data["lastName"]),
            middle_name=_optional_str(data.get("middleName")),
            role=str(data["role"]),
            email=_optional_str(data.get("email")),
            phone=_optional_str(data.get("phone")),
            consent_id=str(data["consentId"]),
            consent_version=str(data["consentVersion"]),
        )
        try:
            result = composition.build_add_teacher_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        response = _envelope(request, _teacher_resource(result.teacher), status=201)
        response["Location"] = f"/api/v1/teachers/{result.teacher.id}"
        return response


class TeacherDetailView(_AuthenticatedView):
    """GET/PATCH /api/v1/teachers/{id} - retrieve or update a teacher."""

    @extend_schema(
        tags=[_TAG],
        operation_id="teachers_retrieve",
        summary="Retrieve a teacher",
        request=None,
        responses={
            200: TeacherResponseSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
        },
    )
    def get(self, request: Request, teacher_id: str) -> Response:
        instance = request.path
        query = GetTeacherQuery(requested_by=str(request.user.id), teacher_id=teacher_id)
        try:
            dto = composition.build_get_teacher_handler().handle(query)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _teacher_resource(dto), status=200)

    @extend_schema(
        tags=[_TAG],
        operation_id="teachers_update",
        summary="Update a teacher",
        request=UpdateTeacherRequestSerializer,
        responses={
            200: TeacherResponseSerializer,
            400: OpenApiResponse(ProblemDetailSerializer, description="Malformed request."),
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Teacher is archived."),
        },
    )
    def patch(self, request: Request, teacher_id: str) -> Response:
        instance = request.path
        serializer = UpdateTeacherRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=instance, request=request)
        data = serializer.validated_data
        command = UpdateTeacherCommand(
            requested_by=str(request.user.id),
            teacher_id=teacher_id,
            first_name=str(data["firstName"]),
            last_name=str(data["lastName"]),
            middle_name=_optional_str(data.get("middleName")),
            role=str(data["role"]),
            email=_optional_str(data.get("email")),
            phone=_optional_str(data.get("phone")),
        )
        try:
            result = composition.build_update_teacher_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _teacher_resource(result.teacher), status=200)


class TeacherArchivalView(_AuthenticatedView):
    """POST /api/v1/teachers/{id}/archival - archive a teacher."""

    @extend_schema(
        tags=[_TAG],
        operation_id="teachers_archive",
        summary="Archive a teacher",
        request=None,
        responses={
            200: TeacherResponseSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Invalid transition."),
        },
    )
    def post(self, request: Request, teacher_id: str) -> Response:
        instance = request.path
        command = ArchiveTeacherCommand(requested_by=str(request.user.id), teacher_id=teacher_id)
        try:
            result = composition.build_archive_teacher_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _teacher_resource(result.teacher), status=200)


class TeacherReactivationView(_AuthenticatedView):
    """POST /api/v1/teachers/{id}/reactivation - reactivate an archived teacher."""

    @extend_schema(
        tags=[_TAG],
        operation_id="teachers_reactivate",
        summary="Reactivate a teacher",
        request=None,
        responses={
            200: TeacherResponseSerializer,
            404: OpenApiResponse(ProblemDetailSerializer, description="Not found."),
            409: OpenApiResponse(ProblemDetailSerializer, description="Invalid transition."),
        },
    )
    def post(self, request: Request, teacher_id: str) -> Response:
        instance = request.path
        command = ReactivateTeacherCommand(requested_by=str(request.user.id), teacher_id=teacher_id)
        try:
            result = composition.build_reactivate_teacher_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=instance, request=request)
        return _envelope(request, _teacher_resource(result.teacher), status=200)
