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

from apps.applications.application.dto import SubmissionOperationResultDto, SubmissionView
from apps.applications.application.dto.commands import (
    AddParticipantCommand,
    AddTeacherCommand,
    CalculatePriceCommand,
    RemoveParticipantCommand,
    RemoveTeacherCommand,
    SetParticipantMemberCountCommand,
    SetParticipantMembersCommand,
    SetPerformanceCommand,
)
from apps.applications.application.dto.queries import GetSubmissionQuery
from apps.applications.application.exceptions import ApplicationError
from apps.applications.infrastructure.revisions import note_submission_revision
from apps.applications.presentation.api.v1 import problems
from apps.applications.presentation.api.v1.files import file_url
from apps.applications.presentation.api.v1.submissions import composition
from apps.applications.presentation.api.v1.submissions.content_serializers import (
    AddParticipantRequestSerializer,
    CreditTeacherRequestSerializer,
    SetParticipantMemberCountRequestSerializer,
    SetParticipantMembersRequestSerializer,
    SetPerformanceRequestSerializer,
    SubmissionProblemDetailSerializer,
    SubmissionResponseSerializer,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication

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
        "editable": dto.editable,
        "performance": (
            {
                "title": performance.title,
                "durationSeconds": performance.duration_seconds,
                "nominationId": performance.nomination_id,
                "disciplineId": performance.discipline_id,
                "ageCategoryId": performance.age_category_id,
                "participantGroupId": performance.participant_group_id,
                "participationFormatId": performance.participation_format_id,
                "comment": performance.comment,
                "ageComposition": performance.age_composition,
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
                # The named people in a collective; empty unless the applicant asked
                # for an individual document each.
                "members": list(p.members),
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
        "attachments": [
            {"id": a.id, "type": a.type, "fileReference": file_url(a.file_reference), "caption": a.caption, "sizeBytes": a.size_bytes}
            for a in dto.attachments
        ],
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


def _note(submission_id: str, change: str, result: SubmissionOperationResultDto) -> None:
    """Journal one applicant edit against whichever placed order carries this performance.

    A no-op while the order is still a draft — the journal decides that. The
    performance's own title is appended when it has one, because an organizer reading
    "добавлен педагог" wants to know to *which* number of a multi-entry application.
    """
    performance = result.submission.performance
    title = (performance.title if performance is not None else "") or ""
    note_submission_revision(submission_id=submission_id, change=f"{change} (выступление «{title}»)" if title.strip() else change)


class _AuthenticatedView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
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
            comment=str(data.get("comment") or ""),
            age_composition=str(data.get("ageComposition") or ""),
        )
        try:
            result = composition.build_set_performance_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _note(submission_id, "Изменены данные выступления", result)
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
        who = " ".join(filter(None, [command.last_name, command.first_name])).strip() or command.display_name or ""
        _note(submission_id, f"Добавлен участник: {who}" if who else "Добавлен участник", result)
        return _result(request, result, status=201)


class SubmissionParticipantMemberCountView(_AuthenticatedView):
    """PUT /api/v1/submissions/{id}/participants/{participantId}/member-count - correct a collective's headcount."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_set_participant_member_count",
        summary="Correct how many people a collective entry stands for",
        description=(
            "Changes the entry rather than replacing it, so the roster of named members already typed "
            "against it survives. The headcount drives the participant-count band check and per-participant pricing."
        ),
        request=SetParticipantMemberCountRequestSerializer,
        responses={200: SubmissionResponseSerializer, 400: OpenApiResponse(SubmissionProblemDetailSerializer, description="Malformed.")},
    )
    def put(self, request: Request, submission_id: str, participant_id: str) -> Response:
        serializer = SetParticipantMemberCountRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        member_count = int(serializer.validated_data["memberCount"])
        command = SetParticipantMemberCountCommand(
            submission_id=submission_id,
            requested_by=_uid(request),
            participant_id=participant_id,
            member_count=member_count,
        )
        try:
            result = composition.build_set_participant_member_count_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        _note(submission_id, f"Указана численность коллектива: {member_count} чел.", result)
        return _result(request, result, status=200)


class SubmissionParticipantMembersView(_AuthenticatedView):
    """PUT /api/v1/submissions/{id}/participants/{participantId}/members - name a collective's members."""

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_set_participant_members",
        summary="Name the people in a collective",
        description=(
            "Replaces the collective's roster of ФИО. Filling it in is how the applicant asks for an "
            "individual diploma per person alongside the collective's own; sending an empty list withdraws that."
        ),
        request=SetParticipantMembersRequestSerializer,
        responses={200: SubmissionResponseSerializer, 400: OpenApiResponse(SubmissionProblemDetailSerializer, description="Malformed.")},
    )
    def put(self, request: Request, submission_id: str, participant_id: str) -> Response:
        serializer = SetParticipantMembersRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        members = tuple(str(name) for name in serializer.validated_data["members"])
        command = SetParticipantMembersCommand(
            submission_id=submission_id,
            requested_by=_uid(request),
            participant_id=participant_id,
            members=members,
        )
        try:
            result = composition.build_set_participant_members_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        named = len([name for name in members if name.strip()])
        _note(submission_id, f"Указан состав коллектива: {named} чел." if named else "Состав коллектива очищен", result)
        return _result(request, result, status=200)


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
        _note(submission_id, "Удалён участник", result)
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
        _note(submission_id, f"Добавлен педагог: {command.last_name} {command.first_name}".strip(), result)
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
        _note(submission_id, "Удалён педагог", result)
        return _result(request, result, status=200)


class SubmissionPriceView(_AuthenticatedView):
    """POST /api/v1/submissions/{id}/price - calculate and freeze the price snapshot.

    A combination the competition never priced answers 200 with the submission left
    unpriced: pricing is optional, so there is nothing exceptional to report.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="submissions_calculate_price",
        summary="Calculate the price",
        request=None,
        responses={200: SubmissionResponseSerializer, 422: OpenApiResponse(SubmissionProblemDetailSerializer, description="Not editable.")},
    )
    def post(self, request: Request, submission_id: str) -> Response:
        command = CalculatePriceCommand(submission_id=submission_id, requested_by=_uid(request))
        try:
            result = composition.build_calculate_price_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)
        return _result(request, result, status=200)
