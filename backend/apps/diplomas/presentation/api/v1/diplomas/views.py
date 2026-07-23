"""Diplomas workspace REST surface (organizer-only).

MVP endpoints: read the template library (with usage counts) and manage the
assignment mechanism that binds a template to a (competition, nomination) pair.
Generation and archive are future work and have no endpoints yet.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diplomas.domain.exceptions import DiplomaError
from apps.diplomas.presentation.api.v1 import problems
from apps.diplomas.presentation.api.v1.diplomas import composition
from apps.diplomas.presentation.api.v1.diplomas.serializers import (
    AssignmentResponseSerializer,
    CreateAssignmentRequestSerializer,
    CreateTemplateRequestSerializer,
    TemplateResponseSerializer,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.presentation.permissions import IsOrganizationStaff

_TAG = "Diplomas"


class _StaffView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)


class DiplomaTemplatesView(_StaffView):
    """The reusable template library."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_templates_list",
        responses={200: TemplateResponseSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        return problems.envelope(request, composition.list_templates())

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_create_template",
        request=CreateTemplateRequestSerializer,
        responses={201: TemplateResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateTemplateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        template = composition.create_template(
            name=str(data["name"]),
            description=str(data.get("description") or ""),
        )
        return problems.envelope(request, template, status=201)


class DiplomaAssignmentsView(_StaffView):
    """List and create template assignments."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_assignments_list",
        responses={200: AssignmentResponseSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        return problems.envelope(request, composition.list_assignments())

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_create_assignment",
        request=CreateAssignmentRequestSerializer,
        responses={201: AssignmentResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateAssignmentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        try:
            assignment = composition.create_assignment(
                competition_id=str(data["competitionId"]),
                category_id=str(data["categoryId"]),
                template_id=str(data["templateId"]),
            )
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        return problems.envelope(request, assignment, status=201)


class DiplomaAssignmentDetailView(_StaffView):
    """Delete a single template assignment."""

    @extend_schema(
        tags=[_TAG],
        operation_id="diplomas_delete_assignment",
        responses={204: None},
    )
    def delete(self, request: Request, assignment_id: str) -> Response:
        try:
            composition.delete_assignment(assignment_id)
        except DiplomaError as exc:
            return problems.diploma_problem(exc, instance=request.path, request=request)
        rid = problems.request_id(request)
        return Response(status=204, headers={"X-Request-ID": rid})
