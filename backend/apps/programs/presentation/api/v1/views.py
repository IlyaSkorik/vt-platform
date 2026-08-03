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
from urllib.parse import quote

from django.http import HttpResponse
from django.http.response import HttpResponseBase
from drf_spectacular.types import OpenApiTypes
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
    AddColumnCommand,
    AddPerformanceCommand,
    CreateProgramCommand,
    CreateShareCommand,
    EditItemCommand,
    FillCellsCommand,
    RenameColumnCommand,
    ReorderItemsCommand,
    UpdateProgramCommand,
    UpdateShareCommand,
)
from apps.programs.application.interfaces import CatalogPerformance
from apps.programs.composition import build_program_service
from apps.programs.domain.exceptions import ProgramError
from apps.programs.presentation.api.v1 import problems
from apps.programs.presentation.api.v1.serializers import (
    AddBlockRequestSerializer,
    AddPerformanceRequestSerializer,
    ColumnRequestSerializer,
    CreateProgramRequestSerializer,
    CreateShareRequestSerializer,
    EditItemRequestSerializer,
    FillCellsRequestSerializer,
    ProgramCandidateSerializer,
    ProgramDetailSerializer,
    ProgramProblemDetailSerializer,
    ProgramShareResourceSerializer,
    ProgramSummarySerializer,
    ReorderItemsRequestSerializer,
    UpdateProgramRequestSerializer,
    UpdateShareRequestSerializer,
)
from config.archive import ArchiveMember, zip_response

_TAG = "Competition Program"

__all__ = [
    "ProgramCandidatesView",
    "ProgramCollectionView",
    "ProgramColumnCollectionView",
    "ProgramColumnDetailView",
    "ProgramDetailView",
    "ProgramExportView",
    "ProgramItemCellsView",
    "ProgramItemCollectionView",
    "ProgramItemDetailView",
    "ProgramItemNumbersView",
    "ProgramItemOrderView",
    "ProgramItemsFillView",
    "ProgramProgressView",
    "ProgramShareCollectionView",
    "ProgramShareDetailView",
]

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(ProgramProblemDetailSerializer, description="Malformed."),
    404: OpenApiResponse(ProgramProblemDetailSerializer, description="Not found."),
    409: OpenApiResponse(ProgramProblemDetailSerializer, description="Conflict."),
    422: OpenApiResponse(ProgramProblemDetailSerializer, description="Unprocessable."),
}


def _pdf_name(title: str) -> str:
    """A filename a person recognises: the programme's own name, path-safe."""
    return f"{_download_stem(title)}.pdf"


def _download_stem(title: str) -> str:
    """The programme's own name, reduced to what a filename may carry."""
    cleaned = "".join(char if char.isalnum() or char in " -_" else " " for char in title).strip()
    return " ".join(cleaned.split()) or "Программа"


def _columns_json(columns: tuple[dto.ColumnView, ...]) -> list[dict[str, Any]]:
    return [{"key": column.key, "label": column.label, "custom": column.custom} for column in columns]


def _share_json(share: dto.ProgramShareView) -> dict[str, Any]:
    return {
        "id": share.id,
        "name": share.name,
        "slug": share.slug,
        "path": share.path,
        "columns": _columns_json(share.columns),
        "itemCount": share.item_count,
        "coversWholeProgram": share.covers_whole_program,
        "controlsRunningOrder": share.controls_running_order,
        "createdAt": share.created_at,
    }


def _item_json(item: dto.ProgramItemView) -> dict[str, Any]:
    return {
        "id": item.id,
        "kind": item.kind,
        "title": item.title,
        "number": item.number,
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
        "participantGroup": item.participant_group,
        "participationFormat": item.participation_format,
        "organization": item.organization,
        "comment": item.comment,
        "missingPerformance": item.missing_performance,
        "customValues": dict(item.custom_values),
        "progress": item.progress,
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
        "availableColumns": _columns_json(view.available_columns),
        "numbersFrozen": view.numbers_frozen,
        "numbersFrozenAt": view.numbers_frozen_at,
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
        "participantGroup": performance.participant_group,
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
    """``PUT`` the complete running order, top to bottom.

    Numbers are untouched: the rows move, the numbers stay with their slots.
    """

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


class ProgramItemNumbersView(_StaffView):
    """``POST`` to re-issue numbers 1..N along the current order.

    Explicitly opt-in, and never a side effect of reordering: it invalidates every number
    already told to a participant.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="programsRenumberItems",
        request=None,
        responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, program_id: str) -> Response:
        try:
            program = build_program_service().renumber_items(program_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))


class ProgramColumnCollectionView(_StaffView):
    """``POST`` a column of the organizer's own onto this programme's table."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsAddColumn",
        request=ColumnRequestSerializer,
        responses={201: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, program_id: str) -> Response:
        serializer = ColumnRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        try:
            program = build_program_service().add_column(AddColumnCommand(program_id=program_id, title=str(serializer.validated_data["title"])))
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program), status=201)


class ProgramColumnDetailView(_StaffView):
    """``PATCH`` a custom column's title; ``DELETE`` the column and its values."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsRenameColumn",
        request=ColumnRequestSerializer,
        responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, program_id: str, column_id: str) -> Response:
        serializer = ColumnRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        try:
            program = build_program_service().rename_column(
                RenameColumnCommand(program_id=program_id, column_id=column_id, title=str(serializer.validated_data["title"]))
            )
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))

    @extend_schema(tags=[_TAG], operation_id="programsRemoveColumn", responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, program_id: str, column_id: str) -> Response:
        try:
            program = build_program_service().remove_column(program_id=program_id, column_id=column_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))


class ProgramItemCellsView(_StaffView):
    """``PUT`` the hand-filled cells of one row (a blank value clears one)."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsFillCells",
        request=FillCellsRequestSerializer,
        responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request, program_id: str, item_id: str) -> Response:
        serializer = FillCellsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        values = tuple((str(key), str(value)) for key, value in serializer.validated_data["values"].items())
        try:
            program = build_program_service().fill_cells(FillCellsCommand(program_id=program_id, item_id=item_id, values=values))
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))


class ProgramExportView(_StaffView):
    """``GET`` the programme as a PDF table of the chosen columns.

    A ``GET`` because it is a download: the organizer picks columns, the browser saves a
    file. Columns arrive as a comma-separated list so the URL stays something that can be
    copied, bookmarked, or wired into a print button; omitting them exports every column.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="programsExportPdf",
        parameters=[
            OpenApiParameter(
                "columns",
                str,
                required=False,
                description="Comma-separated column keys (built-in names or custom:<uuid>). Omit for all.",
            )
        ],
        responses={
            (200, "application/pdf"): OpenApiTypes.BINARY,
            **_PROBLEM_RESPONSES,
        },
    )
    def get(self, request: Request, program_id: str) -> HttpResponse | Response:
        raw = (request.query_params.get("columns") or "").strip()
        columns = tuple(key.strip() for key in raw.split(",") if key.strip())
        try:
            service = build_program_service()
            table = service.program_table(program_id=program_id, columns=columns)
            document = service.export_pdf(program_id=program_id, columns=columns)
        except ProgramError as exc:
            return self._problem(exc, request)
        response = HttpResponse(document, content_type="application/pdf")
        # ``filename*`` carries the real, Cyrillic name; the ASCII ``filename`` is the
        # fallback for clients that ignore RFC 5987.
        response["Content-Disposition"] = f"attachment; filename=\"programme.pdf\"; filename*=UTF-8''{quote(_pdf_name(table.title))}"
        return response


class ProgramMusicArchiveView(_StaffView):
    """``GET`` every backing track of the programme as one ZIP, named by number.

    A ``GET`` for the same reason the PDF export is one: it is a download the
    organizer hands to the sound desk. Nothing is stored — the archive is assembled
    from the already-uploaded files on each request, so it can never be stale.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="programsDownloadMusic",
        responses={
            (200, "application/zip"): OpenApiTypes.BINARY,
            **_PROBLEM_RESPONSES,
        },
    )
    # `HttpResponseBase`, not `HttpResponse`: a ZIP download is a `FileResponse`, which
    # descends from `StreamingHttpResponse` and so is not an `HttpResponse` at all. The
    # base class is the only type that covers a streamed body and a DRF `Response` both.
    def get(self, request: Request, program_id: str) -> HttpResponseBase | Response:
        try:
            archive = build_program_service().music_archive(program_id=program_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        members = [ArchiveMember(arcname=file.filename, reference=file.reference) for file in archive.files]
        notes = [f"Без фонограммы: {label}" for label in archive.missing]
        return zip_response(members, filename=f"{_download_stem(archive.title)} — фонограммы.zip", notes=notes)


class ProgramProgressView(_StaffView):
    """``DELETE`` to put every slot back to pending (the organizer's reset)."""

    @extend_schema(tags=[_TAG], operation_id="programsResetProgress", responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, program_id: str) -> Response:
        try:
            program = build_program_service().reset_progress(program_id)
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
            columns=tuple(str(column) for column in data.get("columns") or ()),
            item_ids=tuple(str(item_id) for item_id in data.get("itemIds") or ()),
            controls_running_order=bool(data.get("controlsRunningOrder")),
        )
        try:
            program, share = build_program_service().create_share(command)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, {"share": _share_json(share), "program": _program_json(program)}, status=201)


class ProgramShareDetailView(_StaffView):
    """``PATCH`` one public edition's name or columns; ``DELETE`` to revoke it."""

    @extend_schema(
        tags=[_TAG],
        operation_id="programsUpdateShare",
        request=UpdateShareRequestSerializer,
        responses={200: ProgramShareResourceSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, program_id: str, share_id: str) -> Response:
        serializer = UpdateShareRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        if not data:
            return problems.validation_problem(
                {"non_field_errors": ["Send a name, a set of columns, or both."]},
                instance=request.get_full_path(),
                request=request,
            )
        command = UpdateShareCommand(
            program_id=program_id,
            share_id=share_id,
            name=str(data["name"]) if "name" in data else None,
            columns=tuple(str(column) for column in data["columns"]) if "columns" in data else None,
            controls_running_order=bool(data["controlsRunningOrder"]) if "controlsRunningOrder" in data else None,
        )
        try:
            program, share = build_program_service().update_share(command)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, {"share": _share_json(share), "program": _program_json(program)})

    @extend_schema(tags=[_TAG], operation_id="programsRemoveShare", responses={200: ProgramDetailSerializer, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, program_id: str, share_id: str) -> Response:
        try:
            program = build_program_service().remove_share(program_id=program_id, share_id=share_id)
        except ProgramError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _program_json(program))
