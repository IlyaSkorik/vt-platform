"""Submission content controllers for the Applications REST API v1.

Building a submission's competitive content: its single performance, its
participants and its teachers, plus price calculation and full retrieval. Each view
is a thin adapter over an application handler; all are owner-scoped (the applicant
is the JWT subject). These endpoints let the Registration Wizard assemble each
performance before the order is submitted.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from apps.applications.application.dto import SubmissionOperationResultDto, SubmissionView
from apps.applications.application.dto.commands import (
    AddParticipantCommand,
    AddTeacherCommand,
    CalculatePriceCommand,
    RemoveParticipantCommand,
    RemoveTeacherCommand,
    SetPerformanceCommand,
)
from apps.applications.application.dto.queries import GetSubmissionQuery
from apps.applications.application.exceptions import ApplicationError
from apps.applications.presentation.api.v1 import problems
from apps.applications.presentation.api.v1.submissions import composition
from apps.applications.presentation.api.v1.submissions.content_serializers import (
    AddParticipantRequestSerializer,
    CreditTeacherRequestSerializer,
    SetPerformanceRequestSerializer,
    SubmissionProblemDetailSerializer,
    SubmissionResponseSerializer,
)

_TAG = "Submissions"


def _iso(value: Any) -> Any:
    return None if value is None else value.isoformat().replace("+00:00", "Z")


def _submission_resource(dto: SubmissionView) -> dict[str, Any]:
    performance = dto.performance
    price = dto.price
    return {
        "id": dto.id,
        "type": "submission",
        "competitionId": dto.competition_id,
        "status": dto.status,
        "performance": (
            {
                "title": performance.title,
                "durationSeconds": performance.duration_seconds,
                "nominationId": performance.nomination_id,
                "disciplineId": performance.discipline_id,
                "ageCategoryId": performance.age_category_id,
                "participantGroupId": performance.participant_group_id,
                "participationFormatId": performance.participation_format_id,
            }
            if performance is not None
            else None
        ),
        "participants": [
            {
                "id": p.id,
                "registryParticipantId": p.registry_participant_id,
                "displayName": p.display_name,
                "firstName": p.first_name,
                "lastName": p.last_name,
                "middleName": p.middle_name,
                "birthDate": p.birth_date.isoformat() if p.birth_date is not None else None,
                "gender": p.gender,
                "memberCount": p.member_count,
            }
            for p in dto.participants
        ],
        "teachers": [
            {
                "id": t.id,
                "teacherDirectoryId": t.directory_teacher_id,
                "firstName": t.first_name,
                "lastName": t.last_name,
                "middleName": t.middle_name,
                "role": t.role,
            }
            for t in dto.teachers
        ],
        "attachments": [{"id": a.id, "type": a.type, "fileReference": a.file_reference, "caption": a.caption} for a in dto.attachments],
        "statusHistory": [
            {"fromStatus": from_status, "toStatus": to_status, "occurredAt": _iso(occurred_at)}
            for from_status, to_status, occurred_at in dto.status_history
        ],
        "price": ({"amount": price.amount, "currency": price.currency, "calculatedAt": _iso(price.calculated_at)} if price is not None else None),
        "createdAt": _iso(dto.created_at),
        "updatedAt": _iso(dto.updated_at),
    }


def _envelope(request: Request, data: Any, *, status: int) -> Response:
    correlation_id = problems.request_id(request)
    return Response({"data": data, "meta": {"requestId": correlation_id}}, status=status, headers={"X-Request-ID": correlation_id})


def _uid(request: Request) -> str:
    return str(request.user.id)


def _result(request: Request, result: SubmissionOperationResultDto, *, status: int) -> Response:
    return _envelope(request, _submission_resource(result.submission), status=status)


class _AuthenticatedView(APIView):
    authentication_classes = (JWTStatelessUserAuthentication,)
    permission_classes = (IsAuthenticated,)


class SubmissionDetailView(_AuthenticatedView):
    """GET /api/v1/submissions/{id} - retrieve one submission in full."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_retrieve",
        summary="Retrieve a submission",
        request=None,
        responses={200: SubmissionResponseSerializer, 404: OpenApiResponse(SubmissionProblemDetailSerializer, description="Not found.")},
    )
    def get(self, request: Request, submission_id: str) -> Response:
        try:
            dto = composition.build_get_submission_handler().handle(GetSubmissionQuery(submission_id=submission_id, requested_by=_uid(request)))
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _envelope(request, _submission_resource(dto), status=200)


class SubmissionPerformanceView(_AuthenticatedView):
    """PUT /api/v1/submissions/{id}/performance - set or replace the performance."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_set_performance",
        summary="Set the performance",
        request=SetPerformanceRequestSerializer,
        responses={200: SubmissionResponseSerializer, 400: OpenApiResponse(SubmissionProblemDetailSerializer, description="Malformed.")},
    )
    def put(self, request: Request, submission_id: str) -> Response:
        serializer = SetPerformanceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        command = SetPerformanceCommand(
            submission_id=submission_id,
            requested_by=_uid(request),
            title=str(data["title"]),
            duration_seconds=int(data["durationSeconds"]),
            nomination_id=str(data["nominationId"]),
            discipline_id=str(data["disciplineId"]),
            age_category_id=str(data["ageCategoryId"]),
            participant_group_id=str(data["participantGroupId"]),
            participation_format_id=str(data["participationFormatId"]),
        )
        try:
            result = composition.build_set_performance_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _result(request, result, status=200)


class SubmissionParticipantsView(_AuthenticatedView):
    """POST /api/v1/submissions/{id}/participants - add a participant."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_add_participant",
        summary="Add a participant",
        request=AddParticipantRequestSerializer,
        responses={201: SubmissionResponseSerializer, 400: OpenApiResponse(SubmissionProblemDetailSerializer, description="Malformed.")},
    )
    def post(self, request: Request, submission_id: str) -> Response:
        serializer = AddParticipantRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data

        def _opt(key: str) -> str | None:
            value = data.get(key)
            return str(value) if value else None

        member_count = data.get("memberCount")
        command = AddParticipantCommand(
            submission_id=submission_id,
            requested_by=_uid(request),
            registry_participant_id=_opt("participantRegistryId"),
            display_name=_opt("displayName"),
            first_name=_opt("firstName"),
            last_name=_opt("lastName"),
            middle_name=_opt("middleName"),
            birth_date=_opt("birthDate"),
            gender=_opt("gender"),
            member_count=int(member_count) if member_count else 1,
        )
        try:
            result = composition.build_add_participant_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _result(request, result, status=201)


class SubmissionParticipantDetailView(_AuthenticatedView):
    """DELETE /api/v1/submissions/{id}/participants/{participantId} - remove a participant."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_remove_participant",
        summary="Remove a participant",
        request=None,
        responses={200: SubmissionResponseSerializer, 404: OpenApiResponse(SubmissionProblemDetailSerializer, description="Not found.")},
    )
    def delete(self, request: Request, submission_id: str, participant_id: str) -> Response:
        command = RemoveParticipantCommand(submission_id=submission_id, requested_by=_uid(request), participant_id=participant_id)
        try:
            result = composition.build_remove_participant_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _result(request, result, status=200)


class SubmissionTeachersView(_AuthenticatedView):
    """POST /api/v1/submissions/{id}/teachers - credit a teacher."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_add_teacher",
        summary="Credit a teacher",
        request=CreditTeacherRequestSerializer,
        responses={201: SubmissionResponseSerializer, 400: OpenApiResponse(SubmissionProblemDetailSerializer, description="Malformed.")},
    )
    def post(self, request: Request, submission_id: str) -> Response:
        serializer = CreditTeacherRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        middle = data.get("middleName")
        directory_teacher_id = data.get("teacherDirectoryId")
        command = AddTeacherCommand(
            submission_id=submission_id,
            requested_by=_uid(request),
            first_name=str(data["firstName"]),
            last_name=str(data["lastName"]),
            middle_name=str(middle) if middle else None,
            role=str(data["role"]),
            directory_teacher_id=str(directory_teacher_id) if directory_teacher_id else None,
        )
        try:
            result = composition.build_add_teacher_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _result(request, result, status=201)


class SubmissionTeacherDetailView(_AuthenticatedView):
    """DELETE /api/v1/submissions/{id}/teachers/{teacherId} - remove a credited teacher."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_remove_teacher",
        summary="Remove a teacher",
        request=None,
        responses={200: SubmissionResponseSerializer, 404: OpenApiResponse(SubmissionProblemDetailSerializer, description="Not found.")},
    )
    def delete(self, request: Request, submission_id: str, teacher_id: str) -> Response:
        command = RemoveTeacherCommand(submission_id=submission_id, requested_by=_uid(request), teacher_id=teacher_id)
        try:
            result = composition.build_remove_teacher_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _result(request, result, status=200)


class SubmissionPriceView(_AuthenticatedView):
    """POST /api/v1/submissions/{id}/price - calculate and freeze the price snapshot."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_calculate_price",
        summary="Calculate the price",
        request=None,
        responses={200: SubmissionResponseSerializer, 422: OpenApiResponse(SubmissionProblemDetailSerializer, description="No pricing.")},
    )
    def post(self, request: Request, submission_id: str) -> Response:
        command = CalculatePriceCommand(submission_id=submission_id, requested_by=_uid(request))
        try:
            result = composition.build_calculate_price_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _result(request, result, status=200)
