"""Organizer REST edge for the Results bounded context.

Thin adapters over :class:`~apps.results.application.services.ProtocolService`: parse,
delegate, render. Every endpoint is staff-gated, and every write answers with the whole
protocol - a saved award changes whether the protocol can be published and whether what is
public is stale, so a client that renders the response is never showing a stale table.

The application layer's DTOs are reached through the :mod:`dto` module alias rather than
imported by name: ``ProtocolDetailView`` means two different things in a Django codebase,
and the HTTP views keep the name here.
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
from apps.results.application import dto
from apps.results.application.commands import (
    AddRowCommand,
    AwardRowsCommand,
    CreateProtocolCommand,
    PublishProtocolCommand,
    ReorderRowsCommand,
    UpdateProtocolCommand,
)
from apps.results.application.interfaces import CatalogPerformance
from apps.results.composition import build_protocol_service
from apps.results.domain.exceptions import ProtocolError
from apps.results.presentation.api.v1 import problems
from apps.results.presentation.api.v1.serializers import (
    AddRowRequestSerializer,
    AwardRowsRequestSerializer,
    CreateProtocolRequestSerializer,
    ProtocolCandidateSerializer,
    ProtocolDetailSerializer,
    ProtocolProblemDetailSerializer,
    ProtocolSummarySerializer,
    PublicationResultSerializer,
    PublishProtocolRequestSerializer,
    ReorderRowsRequestSerializer,
    UpdateProtocolRequestSerializer,
)

_TAG = "Competition Results"

__all__ = [
    "ProtocolAwardsView",
    "ProtocolCandidatesView",
    "ProtocolCollectionView",
    "ProtocolDetailView",
    "ProtocolPublicationView",
    "ProtocolRowCollectionView",
    "ProtocolRowDetailView",
    "ProtocolRowNumbersView",
    "ProtocolRowOrderView",
    "ProtocolRowSyncView",
]

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(ProtocolProblemDetailSerializer, description="Malformed."),
    404: OpenApiResponse(ProtocolProblemDetailSerializer, description="Not found."),
    409: OpenApiResponse(ProtocolProblemDetailSerializer, description="Conflict."),
    422: OpenApiResponse(ProtocolProblemDetailSerializer, description="Unprocessable."),
}


def _columns_json(columns: tuple[dto.ColumnView, ...]) -> list[dict[str, Any]]:
    return [{"key": column.key, "label": column.label} for column in columns]


def _awards_json(options: tuple[dto.AwardOptionView, ...]) -> list[dict[str, Any]]:
    return [{"value": option.value, "label": option.label, "seniority": option.seniority} for option in options]


def _row_json(row: dto.ProtocolRowView) -> dict[str, Any]:
    return {
        "id": row.id,
        "number": row.number,
        "submissionId": row.submission_id,
        "title": row.title,
        "award": row.award,
        "awardLabel": row.award_label,
        "leadParticipant": row.lead_participant,
        "participants": list(row.participants),
        "teachers": list(row.teachers),
        "nomination": row.nomination,
        "discipline": row.discipline,
        "ageCategory": row.age_category,
        "participantGroup": row.participant_group,
        "participationFormat": row.participation_format,
        "organization": row.organization,
        "missingPerformance": row.missing_performance,
    }


def _protocol_json(view: dto.ProtocolDetailView) -> dict[str, Any]:
    """Render a protocol detail DTO onto its camelCase wire shape."""
    return {
        "id": view.id,
        "competitionId": view.competition_id,
        "nominationId": view.nomination_id,
        "nomination": view.nomination,
        "competitionTitle": view.competition_title,
        "name": view.name,
        "status": view.status,
        "rows": [_row_json(row) for row in view.rows],
        "availableColumns": _columns_json(view.available_columns),
        "publicColumns": _columns_json(view.public_columns),
        "awardOptions": _awards_json(view.award_options),
        "revision": view.revision,
        "slug": view.slug,
        "path": view.path,
        "publishedAt": view.published_at,
        "hasUnpublishedChanges": view.has_unpublished_changes,
        "seededFromProgramId": view.seeded_from_program_id,
        "createdAt": view.created_at,
        "updatedAt": view.updated_at,
        "version": view.version,
    }


def _summary_json(view: dto.ProtocolSummaryView) -> dict[str, Any]:
    return {
        "id": view.id,
        "competitionId": view.competition_id,
        "nominationId": view.nomination_id,
        "nomination": view.nomination,
        "name": view.name,
        "status": view.status,
        "rowCount": view.row_count,
        "decidedCount": view.decided_count,
        "revision": view.revision,
        "slug": view.slug,
        "path": view.path,
        "publishedAt": view.published_at,
        "hasUnpublishedChanges": view.has_unpublished_changes,
        "createdAt": view.created_at,
        "updatedAt": view.updated_at,
    }


def _publication_json(view: dto.PublicationResultView) -> dict[str, Any]:
    return {
        "protocol": _protocol_json(view.protocol),
        "diplomasAwarded": view.diplomas_awarded,
        "diplomasCreated": view.diplomas_created,
        "diplomasMissing": view.diplomas_missing,
        "lettersSent": view.letters_sent,
        "lettersSkipped": view.letters_skipped,
    }


def _candidate_json(performance: CatalogPerformance) -> dict[str, Any]:
    return {
        "submissionId": str(performance.submission_id),
        "title": performance.title,
        "nomination": performance.nomination,
        "discipline": performance.discipline,
        "ageCategory": performance.age_category,
        "participantGroup": performance.participant_group,
        "participationFormat": performance.participation_format,
        "participants": list(performance.participants),
        "teachers": list(performance.teachers),
        "organization": performance.organization,
    }


class _StaffView(APIView):
    """Authenticated organization staff only."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)

    def _problem(self, exc: ProtocolError, request: Request) -> Response:
        return problems.protocol_problem(exc, instance=request.get_full_path(), request=request)


class ProtocolCollectionView(_StaffView):
    """``GET /api/v1/staff/protocols`` - list; ``POST`` - open one for a nomination."""

    @extend_schema(
        tags=[_TAG],
        operation_id="protocolsList",
        parameters=[OpenApiParameter("competitionId", str, required=True, description="The competition whose protocols to list.")],
        responses={200: ProtocolSummarySerializer(many=True), **_PROBLEM_RESPONSES},
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
            summaries = build_protocol_service().list_protocols(competition_id=competition_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, [_summary_json(summary) for summary in summaries], meta={"total": len(summaries)})

    @extend_schema(
        tags=[_TAG],
        operation_id="protocolsCreate",
        request=CreateProtocolRequestSerializer,
        responses={201: ProtocolDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateProtocolRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = CreateProtocolCommand(
            competition_id=str(data["competitionId"]),
            nomination_id=str(data["nominationId"]),
            name=str(data["name"]) if data.get("name") else None,
            columns=tuple(data.get("columns") or ()),
            seed=bool(data.get("seed", True)),
        )
        try:
            protocol = build_protocol_service().create_protocol(command)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol), status=201)


class ProtocolDetailView(_StaffView):
    """``GET``, ``PATCH`` and ``DELETE`` one protocol."""

    @extend_schema(tags=[_TAG], operation_id="protocolsRetrieve", responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES})
    def get(self, request: Request, protocol_id: str) -> Response:
        try:
            protocol = build_protocol_service().get_protocol(protocol_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))

    @extend_schema(
        tags=[_TAG],
        operation_id="protocolsUpdate",
        request=UpdateProtocolRequestSerializer,
        responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, protocol_id: str) -> Response:
        serializer = UpdateProtocolRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        # An absent ``columns`` key leaves the selection alone; an empty list is a
        # deliberate reset to the default set, and the two must not be conflated.
        sent_columns = "columns" in request.data if isinstance(request.data, dict) else False
        command = UpdateProtocolCommand(
            protocol_id=protocol_id,
            name=str(data["name"]) if "name" in data else None,
            columns=tuple(data.get("columns") or ()) if sent_columns else None,
        )
        try:
            protocol = build_protocol_service().update_protocol(command)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))

    @extend_schema(tags=[_TAG], operation_id="protocolsDestroy", responses={204: None, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, protocol_id: str) -> Response:
        try:
            build_protocol_service().delete_protocol(protocol_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return Response(status=204)


class ProtocolCandidatesView(_StaffView):
    """``GET`` the competing acts of this nomination that have no row yet."""

    @extend_schema(
        tags=[_TAG],
        operation_id="protocolsCandidates",
        responses={200: ProtocolCandidateSerializer(many=True), **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request, protocol_id: str) -> Response:
        try:
            candidates = build_protocol_service().candidates(protocol_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, [_candidate_json(candidate) for candidate in candidates], meta={"total": len(candidates)})


class ProtocolRowCollectionView(_StaffView):
    """``POST`` one act's line into the protocol."""

    @extend_schema(
        tags=[_TAG],
        operation_id="protocolsAddRow",
        request=AddRowRequestSerializer,
        responses={201: ProtocolDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, protocol_id: str) -> Response:
        serializer = AddRowRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = AddRowCommand(
            protocol_id=protocol_id,
            submission_id=str(data["submissionId"]),
            position=data.get("position"),
            award=data.get("award"),
        )
        try:
            protocol = build_protocol_service().add_row(command)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol), status=201)


class ProtocolRowSyncView(_StaffView):
    """``POST`` to pull in every act of this nomination that has no row yet.

    Append-only: existing rows keep their place **and their award**, so this is safe to
    press after results have been entered.
    """

    @extend_schema(tags=[_TAG], operation_id="protocolsSyncRows", request=None, responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES})
    def post(self, request: Request, protocol_id: str) -> Response:
        try:
            protocol = build_protocol_service().sync_from_running_order(protocol_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))


class ProtocolRowDetailView(_StaffView):
    """``DELETE`` one row of the protocol."""

    @extend_schema(tags=[_TAG], operation_id="protocolsRemoveRow", responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, protocol_id: str, row_id: str) -> Response:
        try:
            protocol = build_protocol_service().remove_row(protocol_id=protocol_id, row_id=row_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))


class ProtocolRowOrderView(_StaffView):
    """``PUT`` a new order for the protocol's rows."""

    @extend_schema(
        tags=[_TAG],
        operation_id="protocolsReorderRows",
        request=ReorderRowsRequestSerializer,
        responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request, protocol_id: str) -> Response:
        serializer = ReorderRowsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        command = ReorderRowsCommand(protocol_id=protocol_id, row_ids=tuple(str(row_id) for row_id in serializer.validated_data["rowIds"]))
        try:
            protocol = build_protocol_service().reorder_rows(command)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))


class ProtocolRowNumbersView(_StaffView):
    """``POST`` to re-issue numbers 1..N along the current order.

    Its own endpoint precisely because it invalidates numbers participants may already have
    been told, and so must never happen as a side effect of a reorder.
    """

    @extend_schema(tags=[_TAG], operation_id="protocolsRenumberRows", request=None, responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES})
    def post(self, request: Request, protocol_id: str) -> Response:
        try:
            protocol = build_protocol_service().renumber_rows(protocol_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))


class ProtocolAwardsView(_StaffView):
    """``PUT`` the results, ``DELETE`` to clear them all.

    The endpoint the jury tab exists for. ``PUT`` takes one award or a whole nomination's
    worth in a single request, and is deliberately repeatable: a jury revising a decision is
    the normal case, not an exception.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="protocolsAwardRows",
        request=AwardRowsRequestSerializer,
        responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request, protocol_id: str) -> Response:
        serializer = AwardRowsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        entries = serializer.validated_data["awards"]
        command = AwardRowsCommand(
            protocol_id=protocol_id,
            awards=tuple((str(entry["rowId"]), entry.get("award")) for entry in entries),
        )
        try:
            protocol = build_protocol_service().award_rows(command)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))

    @extend_schema(tags=[_TAG], operation_id="protocolsClearAwards", responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, protocol_id: str) -> Response:
        try:
            protocol = build_protocol_service().clear_awards(protocol_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))


class ProtocolPublicationView(_StaffView):
    """``POST`` to publish the results, ``DELETE`` to take them back off the page.

    Publishing is three effects in one action - the public page, the diplomas, the letters -
    so the response carries what each of them did rather than just the protocol's new status.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="protocolsPublish",
        request=PublishProtocolRequestSerializer,
        responses={200: PublicationResultSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, protocol_id: str) -> Response:
        serializer = PublishProtocolRequestSerializer(data=request.data or {})
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        sent_columns = "columns" in request.data if isinstance(request.data, dict) else False
        command = PublishProtocolCommand(
            protocol_id=protocol_id,
            columns=tuple(data.get("columns") or ()) if sent_columns else None,
            notify=bool(data.get("notify", True)),
        )
        try:
            result = build_protocol_service().publish(command)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _publication_json(result))

    @extend_schema(tags=[_TAG], operation_id="protocolsUnpublish", responses={200: ProtocolDetailSerializer, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, protocol_id: str) -> Response:
        try:
            protocol = build_protocol_service().unpublish(protocol_id)
        except ProtocolError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, _protocol_json(protocol))
