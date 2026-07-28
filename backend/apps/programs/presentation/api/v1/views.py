"""Organizer REST edge for the Programs bounded context.

Thin adapters over :class:`~apps.programs.application.services.ProgramService`: parse,
delegate, render. Every endpoint is staff-gated, and every write answers with the
whole recomputed program - inserting a break moves everything after it, so a client
that renders the response is never showing a stale timetable.

The application layer's DTOs are reached through the :mod:`dto` module alias rather
than imported by name: ``ProgramDetailView`` means two different things in a Django
codebase, and the HTTP views keep the name here.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.presentation.permissions import IsOrganizationStaff
from apps.programs.application import dto
from apps.programs.application.commands import (
    AddBlockCommand,
    AddPerformanceCommand,
    CreateProgramCommand,
    CreateShareCommand,
    EditItemCommand,
    ReorderItemsCommand,
    UpdateProgramCommand,
)
from apps.programs.application.interfaces import CatalogPerformance
from apps.programs.composition import build_program_service
from apps.programs.domain.exceptions import ProgramError
from apps.programs.presentation.api.v1 import problems
from apps.programs.presentation.api.v1.serializers import (
    AddBlockRequestSerializer,
    AddPerformanceRequestSerializer,
    CreateProgramRequestSerializer,
    CreateShareRequestSerializer,
    EditItemRequestSerializer,
    ProgramCandidateSerializer,
    ProgramDetailSerializer,
    ProgramProblemDetailSerializer,
    ProgramShareResourceSerializer,
    ProgramSummarySerializer,
    ReorderItemsRequestSerializer,
    UpdateProgramRequestSerializer,
)

_TAG = "Competition Program"

__all__ = [
    "ProgramCandidatesView",
    "ProgramCollectionView",
    "ProgramDetailView",
    "ProgramItemCollectionView",
    "ProgramItemDetailView",
    "ProgramItemOrderView",
    "ProgramItemsFillView",
    "ProgramShareCollectionView",
    "ProgramShareDetailView",
]

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(ProgramProblemDetailSerializer, description="Malformed."),
    404: OpenApiResponse(ProgramProblemDetailSerializer, description="Not found."),
    409: OpenApiResponse(ProgramProblemDetailSerializer, description="Conflict."),
    422: OpenApiResponse(ProgramProblemDetailSerializer, description="Unprocessable."),
}


def _share_json(share: dto.ProgramShareView) -> dict[str, Any]:
    return {
        "id": share.id,
        "name": share.name,
        "slug": share.slug,
        "path": share.path,
        "itemCount": share.item_count,
        "coversWholeProgram": share.covers_whole_program,
        "createdAt": share.created_at,
    }


def _item_json(item: dto.ProgramItemView) -> dict[str, Any]:
    return {
        "id": item.id,
        "kind": item.kind,
        "title": item.title,
        "durationSeconds": item.duration_seconds,
        "schedule": {
            "position": item.schedule.position,
            "offsetSeconds": item.schedule.offset_seconds,
            "slotSeconds": item.schedule.slot_seconds,
            "startsAt": item.schedule.starts_at,
            "endsAt": item.schedule.ends_at,
        },
        "submissionId": item.submission_id,
        "leadParticipant": item.lead_participant,
        "participants": list(item.participants),
        "teachers": list(item.teachers),
        "nomination": item.nomination,
        "discipline": item.discipline,
        "ageCategory": item.age_category,
        "participationFormat": item.participation_format,
        "organization": item.organization,
        "comment": item.comment,
        "missingPerformance": item.missing_performance,
    }


def _program_json(view: dto.ProgramDetailView) -> dict[str, Any]:
    """Render a program detail DTO onto its camelCase wire shape."""
    return {
        "id": view.id,
        "competitionId": view.competition_id,
        "nominationId": view.nomination_id,
        "name": view.name,
        "bufferSeconds": view.buffer_seconds,
        "startsAt": view.starts_at,
        "items": [_item_json(item) for item in view.items],
        "shares": [_share_json(share) for share in view.shares],
        "totalSeconds": view.total_seconds,
        "endsAt": view.ends_at,
        "createdAt": view.created_at,
        "updatedAt": view.updated_at,
        "version": view.version,
    }


def _summary_json(view: dto.ProgramSummaryView) -> dict[str, Any]:
    return {
        "id": view.id,
        "competitionId": view.competition_id,
        "nominationId": view.nomination_id,
        "name": view.name,
        "bufferSeconds": view.buffer_seconds,
        "startsAt": view.starts_at,
        "itemCount": view.item_count,
        "performanceCount": view.performance_count,
        "totalSeconds": view.total_seconds,
        "shareCount": view.share_count,
        "createdAt": view.created_at,
        "updatedAt": view.updated_at,
    }


def _candidate_json(performance: CatalogPerformance) -> dict[str, Any]:
    return {
        "submissionId": str(performance.submission_id),
        "title": performance.title,
        "durationSeconds": performance.duration_seconds,
        "nomination": performance.nomination,
        "discipline": performance.discipline,
        "ageCategory": performance.age_category,
        "participationFormat": performance.participation_format,
        "participants": list(performance.participants),
        "teachers": list(performance.teachers),
        "organization": performance.organization,
        "comment": performance.comment,
    }


class _StaffView(APIView):
    """Authenticated organization staff only."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)

    def _problem(self, exc: ProgramError, request: Request) -> Response:
        return problems.program_problem(exc, instance=request.get_full_path(), request=request)


class ProgramCollectionView(_StaffView):
    """``GET /api/v1/staff/programs`` - list; ``POST`` - create."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsList",
        parameters=[
            OpenApiParameter("competitionId", str, required=True, description="The competition whose programs to list."),
            OpenApiParameter("nominationId", str, required=False, description="Narrow to one nomination."),
        ],
        responses={200: ProgramSummarySerializer(many=True), **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        competition_id = request.query_params.get("competitionId")
        if not competition_id:
            return problems.validation_problem(
                {"competitionId": ["This query parameter is required."]},
                instance=request.get_full_path(),
                request=request,
            )
        try:
            summaries = build_program_service().list_programs(
                competition_id=competition_id,
                nomination_id=request.query_params.get("nominationId"),
            )
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, [_summary_json(summary) for summary in summaries], meta={"total": len(summaries)})

    @extend_schema(
        tags=[_TAG],
        operation_id="programsCreate",
        request=CreateProgramRequestSerializer,
        responses={201: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateProgramRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        nomination_id = data.get("nominationId")
        command = CreateProgramCommand(
            competition_id=str(data["competitionId"]),
            name=str(data["name"]),
            nomination_id=str(nomination_id) if nomination_id else None,
            buffer_seconds=int(data.get("bufferSeconds") or 0),
            starts_at=data.get("startsAt"),
        )
        try:
            program = build_program_service().create_program(command)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program), status=201)


class ProgramDetailView(_StaffView):
    """``GET``, ``PATCH`` and ``DELETE`` one program."""

    @extend_schema(tags=[_TAG], operation_id="programsRetrieve", responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES})
    def get(self, request: Request, program_id: str) -> Response:
        try:
            program = build_program_service().get_program(program_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))

    @extend_schema(
        tags=[_TAG],
        operation_id="programsUpdate",
        request=UpdateProgramRequestSerializer,
        responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, program_id: str) -> Response:
        serializer = UpdateProgramRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        buffer_seconds = data.get("bufferSeconds")
        # ``startsAt: null`` is a deliberate "untime this program"; an absent key is not.
        sent_starts_at = "startsAt" in request.data if isinstance(request.data, dict) else False
        command = UpdateProgramCommand(
            program_id=program_id,
            name=str(data["name"]) if "name" in data else None,
            buffer_seconds=int(buffer_seconds) if buffer_seconds is not None else None,
            starts_at=data.get("startsAt"),
            clear_starts_at=sent_starts_at and data.get("startsAt") is None,
        )
        try:
            program = build_program_service().update_program(command)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))

    @extend_schema(tags=[_TAG], operation_id="programsDestroy", responses={204: None, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, program_id: str) -> Response:
        try:
            build_program_service().delete_program(program_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return Response(status=204)


class ProgramCandidatesView(_StaffView):
    """``GET`` the competing acts of this program's scope that have no slot yet."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsCandidates",
        responses={200: ProgramCandidateSerializer(many=True), **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request, program_id: str) -> Response:
        try:
            candidates = build_program_service().candidates(program_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, [_candidate_json(candidate) for candidate in candidates], meta={"total": len(candidates)})


class ProgramItemCollectionView(_StaffView):
    """``POST`` a slot: an act by ``submissionId``, or a block by title and length."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsAddItem",
        request=AddBlockRequestSerializer,
        responses={201: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, program_id: str) -> Response:
        payload = request.data if isinstance(request.data, dict) else {}
        service = build_program_service()
        try:
            if payload.get("submissionId"):
                performance_request = AddPerformanceRequestSerializer(data=payload)
                if not performance_request.is_valid():
                    return problems.validation_problem(performance_request.errors, instance=request.get_full_path(), request=request)
                performance_data = performance_request.validated_data
                duration = performance_data.get("durationSeconds")
                program = service.add_performance(
                    AddPerformanceCommand(
                        program_id=program_id,
                        submission_id=str(performance_data["submissionId"]),
                        position=performance_data.get("position"),
                        duration_seconds=int(duration) if duration is not None else None,
                    )
                )
            else:
                block_request = AddBlockRequestSerializer(data=payload)
                if not block_request.is_valid():
                    return problems.validation_problem(block_request.errors, instance=request.get_full_path(), request=request)
                block_data = block_request.validated_data
                program = service.add_block(
                    AddBlockCommand(
                        program_id=program_id,
                        title=str(block_data["title"]),
                        duration_seconds=int(block_data["durationSeconds"]),
                        kind=str(block_data.get("kind") or "BREAK"),
                        position=block_data.get("position"),
                    )
                )
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program), status=201)


class ProgramItemsFillView(_StaffView):
    """``POST`` to append every remaining competing act of the program's scope."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsFillItems",
        request=None,
        responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, program_id: str) -> Response:
        try:
            program = build_program_service().fill_from_scope(program_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))


class ProgramItemDetailView(_StaffView):
    """``PATCH`` and ``DELETE`` one slot."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsEditItem",
        request=EditItemRequestSerializer,
        responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, program_id: str, item_id: str) -> Response:
        serializer = EditItemRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        if not data:
            return problems.validation_problem(
                {"non_field_errors": ["Send a title, a duration, or both."]},
                instance=request.get_full_path(),
                request=request,
            )
        duration = data.get("durationSeconds")
        try:
            program = build_program_service().edit_item(
                EditItemCommand(
                    program_id=program_id,
                    item_id=item_id,
                    title=str(data["title"]) if "title" in data else None,
                    duration_seconds=int(duration) if duration is not None else None,
                )
            )
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))

    @extend_schema(tags=[_TAG], operation_id="programsRemoveItem", responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, program_id: str, item_id: str) -> Response:
        try:
            program = build_program_service().remove_item(program_id=program_id, item_id=item_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))


class ProgramItemOrderView(_StaffView):
    """``PUT`` the complete running order, top to bottom."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsReorderItems",
        request=ReorderItemsRequestSerializer,
        responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request, program_id: str) -> Response:
        serializer = ReorderItemsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        item_ids = tuple(str(item_id) for item_id in serializer.validated_data["itemIds"])
        try:
            program = build_program_service().reorder_items(ReorderItemsCommand(program_id=program_id, item_ids=item_ids))
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))


class ProgramShareCollectionView(_StaffView):
    """``GET`` this program's public editions; ``POST`` a new one."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsListShares",
        responses={200: ProgramShareResourceSerializer(many=True), **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request, program_id: str) -> Response:
        try:
            program = build_program_service().get_program(program_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, [_share_json(share) for share in program.shares], meta={"total": len(program.shares)})

    @extend_schema(
        tags=[_TAG],
        operation_id="programsCreateShare",
        request=CreateShareRequestSerializer,
        responses={201: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, program_id: str) -> Response:
        serializer = CreateShareRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = CreateShareCommand(
            program_id=program_id,
            name=str(data["name"]),
            item_ids=tuple(str(item_id) for item_id in data.get("itemIds") or ()),
        )
        try:
            program, share = build_program_service().create_share(command)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, {"share": _share_json(share), "program": _program_json(program)}, status=201)


class ProgramShareDetailView(_StaffView):
    """``DELETE`` one public edition - its link stops resolving at once."""

    @extend_schema(tags=[_TAG], operation_id="programsRemoveShare", responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, program_id: str, share_id: str) -> Response:
        try:
            program = build_program_service().remove_share(program_id=program_id, share_id=share_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))
