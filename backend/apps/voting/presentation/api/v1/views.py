"""Organizer REST edge for the Voting bounded context.

Note that ``BallotDetailView`` here is an HTTP view, not the application DTO of
the same name — the DTOs are reached through :mod:`resources` and never imported
by name, which is what keeps the clash harmless.

Thin adapters over :class:`~apps.voting.application.services.BallotService`: parse,
delegate, render. Every endpoint is staff-gated *and* module-gated — an
organization that was not sold the audience vote is refused here, not merely shown
a panel without the menu item.

Every write answers with the whole recomputed ballot: adding a nominee renumbers
the rest, so a client that renders the response is never showing a stale list.
"""

from __future__ import annotations

import io
import uuid
from typing import Any

import qrcode
from django.http import HttpResponse
from django.http.response import HttpResponseBase
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.domain.value_objects import OrganizationModule
from apps.organization.presentation.permissions import IsModuleEnabled, IsOrganizationStaff
from apps.organization.presentation.scope import callers_organization_id
from apps.voting.application.commands import (
    AddNomineeCommand,
    CreateBallotCommand,
    EditNomineeCommand,
    ImportNomineesCommand,
    NomineeRow,
    ReorderNomineesCommand,
    SeedFromProgramCommand,
    UpdateBallotCommand,
)
from apps.voting.composition import build_ballot_service
from apps.voting.domain.exceptions import BallotError, BallotNotFoundError, InvalidBallotDataError
from apps.voting.infrastructure.models import BallotModel
from apps.voting.presentation.api.v1 import resources, sheets
from apps.voting.presentation.api.v1.problems import ballot_problem, envelope, problem_response, request_id
from apps.voting.presentation.api.v1.serializers import (
    AddNomineeRequestSerializer,
    BallotDetailSerializer,
    BallotProblemDetailSerializer,
    BallotSummarySerializer,
    CreateBallotRequestSerializer,
    EditNomineeRequestSerializer,
    ImportPreviewSerializer,
    ReorderNomineesRequestSerializer,
    SeedFromProgramRequestSerializer,
    UpdateBallotRequestSerializer,
)
from shared.spreadsheet import SheetReadError, xlsx_response

_TAG = "Audience Voting"

__all__ = [
    "BallotCloseView",
    "BallotCollectionView",
    "BallotDetailView",
    "BallotNomineeCollectionView",
    "BallotNomineeDetailView",
    "BallotNomineeImportView",
    "BallotNomineeOrderView",
    "BallotNomineeTemplateView",
    "BallotOpenView",
    "BallotQrView",
    "BallotResultsView",
    "BallotSeedView",
]

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(BallotProblemDetailSerializer, description="Malformed."),
    403: OpenApiResponse(BallotProblemDetailSerializer, description="Module not connected, or not staff."),
    404: OpenApiResponse(BallotProblemDetailSerializer, description="Not found."),
    409: OpenApiResponse(BallotProblemDetailSerializer, description="Conflict."),
    422: OpenApiResponse(BallotProblemDetailSerializer, description="Unprocessable."),
}


class _StaffView(APIView):
    """Authenticated organization staff, whose organization holds the module."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (
        IsAuthenticated,
        IsOrganizationStaff,
        IsModuleEnabled.of(OrganizationModule.VOTING),
    )

    def _problem(self, error: BallotError, request: Request) -> Response:
        return ballot_problem(error, instance=request.get_full_path(), request=request)

    def _organization(self, request: Request) -> uuid.UUID | None:
        return callers_organization_id(request)

    def _owned(self, request: Request, ballot_id: str) -> uuid.UUID:
        """Parse the id and confirm the caller's organization owns that ballot.

        Another organization's ballot is reported as *not found* rather than as
        forbidden: confirming that an id exists is already telling one organization
        something about another. A malformed id gets the same answer, for the same
        reason — the caller learns only that they have nothing here.
        """
        organization_id = self._organization(request)
        try:
            parsed = uuid.UUID(ballot_id)
        except (ValueError, TypeError) as exc:
            raise BallotNotFoundError("Голосование не найдено.") from exc
        if organization_id is None or not _belongs_to(parsed, organization_id):
            raise BallotNotFoundError("Голосование не найдено.")
        return parsed


def _belongs_to(ballot_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
    """Whether this organization owns the ballot — one indexed existence check."""
    return BallotModel.objects.filter(pk=ballot_id, organization_id=organization_id, deleted_at__isnull=True).exists()


class BallotCollectionView(_StaffView):
    """``GET`` the organization's ballots; ``POST`` a new one."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_list_ballots",
        summary="List the organization's ballots",
        parameters=[
            OpenApiParameter(
                name="competitionId",
                description="Narrow to one festival's ballots. Omitted, standalone ballots are listed too.",
                required=False,
                type=str,
            )
        ],
        request=None,
        responses={200: BallotSummarySerializer(many=True), **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        organization_id = self._organization(request)
        if organization_id is None:  # pragma: no cover - the staff gate precedes this
            return envelope([], request)
        raw = request.query_params.get("competitionId")
        try:
            competition_id = uuid.UUID(raw) if raw else None
        except (ValueError, TypeError):
            return problem_response(
                status=400,
                type_suffix="bad-request",
                title="Bad request",
                detail="Некорректный идентификатор фестиваля.",
                instance=request.get_full_path(),
                request=request,
            )
        ballots = build_ballot_service().list_ballots(organization_id, competition_id=competition_id)
        return envelope([resources.ballot_summary(row) for row in ballots], request)

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_create_ballot",
        summary="Create a ballot",
        description="`competitionId` is optional: a ballot may run without a festival on the platform.",
        request=CreateBallotRequestSerializer,
        responses={201: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateBallotRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        organization_id = self._organization(request)
        if organization_id is None:  # pragma: no cover - the staff gate precedes this
            return self._problem(BallotNotFoundError("Голосование не найдено."), request)

        command = CreateBallotCommand(
            organization_id=str(organization_id),
            title=str(payload["title"]),
            competition_id=str(payload["competitionId"]) if payload.get("competitionId") else None,
            description=str(payload.get("description") or ""),
            opens_at=payload.get("opensAt"),
            closes_at=payload.get("closesAt"),
            votes_per_voter=int(payload.get("votesPerVoter", 1)),
            cooldown_hours=int(payload.get("cooldownHours", 0)),
            reveal=str(payload.get("reveal", "AFTER_CLOSE")),
        )
        try:
            detail = build_ballot_service().create(command)
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request, status=201)


class BallotDetailView(_StaffView):
    """``GET``, ``PATCH`` and ``DELETE`` one ballot."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_get_ballot",
        summary="Read one ballot",
        request=None,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request, ballot_id: str) -> Response:
        try:
            detail = build_ballot_service().get(self._owned(request, ballot_id))
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_update_ballot",
        summary="Change a ballot's wording or rules",
        request=UpdateBallotRequestSerializer,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, ballot_id: str) -> Response:
        serializer = UpdateBallotRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            parsed = self._owned(request, ballot_id)
            command = UpdateBallotCommand(
                ballot_id=str(parsed),
                title=str(payload["title"]) if "title" in payload else None,
                description=str(payload["description"]) if "description" in payload else None,
                opens_at=payload.get("opensAt"),
                closes_at=payload.get("closesAt"),
                # Without this flag "clear the closing time" and "leave it alone"
                # are the same payload, and one of them silently never happens.
                window_given="opensAt" in payload or "closesAt" in payload,
                votes_per_voter=int(payload["votesPerVoter"]) if "votesPerVoter" in payload else None,
                cooldown_hours=int(payload["cooldownHours"]) if "cooldownHours" in payload else None,
                reveal=str(payload["reveal"]) if "reveal" in payload else None,
            )
            detail = build_ballot_service().update(command)
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_delete_ballot",
        summary="Retire a ballot",
        description="The votes already cast stay where they are; the public link stops resolving.",
        request=None,
        responses={204: OpenApiResponse(description="Retired."), **_PROBLEM_RESPONSES},
    )
    def delete(self, request: Request, ballot_id: str) -> Response:
        try:
            build_ballot_service().delete(self._owned(request, ballot_id))
        except BallotError as exc:
            return self._problem(exc, request)
        return Response(status=204, headers={"X-Request-ID": request_id(request)})


class BallotOpenView(_StaffView):
    """``POST`` — start accepting votes."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_open_ballot",
        summary="Open a ballot",
        request=None,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, ballot_id: str) -> Response:
        try:
            detail = build_ballot_service().open(self._owned(request, ballot_id))
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)


class BallotCloseView(_StaffView):
    """``POST`` — stop accepting votes, for good."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_close_ballot",
        summary="Close a ballot",
        description="One-way: a ballot that could be reopened is a result that can be revised.",
        request=None,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, ballot_id: str) -> Response:
        try:
            detail = build_ballot_service().close(self._owned(request, ballot_id))
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)


class BallotNomineeCollectionView(_StaffView):
    """``POST`` one more nominee onto the ballot."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_add_nominee",
        summary="Add a nominee",
        request=AddNomineeRequestSerializer,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, ballot_id: str) -> Response:
        serializer = AddNomineeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            parsed = self._owned(request, ballot_id)
            detail = build_ballot_service().add_nominee(AddNomineeCommand(ballot_id=str(parsed), nominee=_nominee_row(payload)))
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)


class BallotNomineeDetailView(_StaffView):
    """``PATCH`` a nominee's card; ``DELETE`` them from the ballot."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_edit_nominee",
        summary="Correct a nominee's card",
        request=EditNomineeRequestSerializer,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, ballot_id: str, nominee_id: str) -> Response:
        serializer = EditNomineeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            parsed = self._owned(request, ballot_id)
            detail = build_ballot_service().edit_nominee(
                EditNomineeCommand(
                    ballot_id=str(parsed),
                    nominee_id=nominee_id,
                    title=str(payload["title"]) if "title" in payload else None,
                    subtitle=str(payload["subtitle"]) if "subtitle" in payload else None,
                    city=str(payload["city"]) if "city" in payload else None,
                    photo=payload.get("photo"),
                    number=payload.get("number"),
                )
            )
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_remove_nominee",
        summary="Take a nominee off the ballot",
        description="Erased outright while nobody has voted for them; withdrawn once somebody has.",
        request=None,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def delete(self, request: Request, ballot_id: str, nominee_id: str) -> Response:
        try:
            parsed = self._owned(request, ballot_id)
            detail = build_ballot_service().remove_nominee(parsed, uuid.UUID(nominee_id))
        except (ValueError, TypeError):
            return self._problem(BallotNotFoundError("Номинанта нет в этом голосовании."), request)
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)


class BallotNomineeOrderView(_StaffView):
    """``POST`` a new running order for the nominee list."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_reorder_nominees",
        summary="Rearrange the nominee list",
        request=ReorderNomineesRequestSerializer,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, ballot_id: str) -> Response:
        serializer = ReorderNomineesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            parsed = self._owned(request, ballot_id)
            detail = build_ballot_service().reorder_nominees(
                ReorderNomineesCommand(
                    ballot_id=str(parsed),
                    order=tuple(str(value) for value in serializer.validated_data["order"]),
                )
            )
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)


class BallotSeedView(_StaffView):
    """``POST`` — fill the list from a running order of this ballot's festival."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_seed_from_program",
        summary="Seed the nominee list from a programme",
        description=(
            "Copies the programme's performances onto the ballot as its own nominees. "
            "Only for a ballot attached to a festival; a standalone one is filled in by hand or from a file."
        ),
        request=SeedFromProgramRequestSerializer,
        responses={200: BallotDetailSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, ballot_id: str) -> Response:
        serializer = SeedFromProgramRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            parsed = self._owned(request, ballot_id)
            detail = build_ballot_service().seed_from_program(
                SeedFromProgramCommand(ballot_id=str(parsed), program_id=str(serializer.validated_data["programId"]))
            )
        except BallotError as exc:
            return self._problem(exc, request)
        return envelope(resources.ballot_detail(detail), request)


class BallotNomineeTemplateView(_StaffView):
    """``GET`` the .xlsx an organizer fills in and sends back.

    Handing out the file is what makes the import usable: without it the organizer
    sends the table they already have, in their own shape, and the two of you spend
    an afternoon on column names.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_nominee_template",
        summary="Download the nominee-list template",
        request=None,
        responses={200: OpenApiResponse(description="An .xlsx with the headings and an example row.")},
    )
    def get(self, request: Request, ballot_id: str) -> HttpResponseBase:
        try:
            self._owned(request, ballot_id)
        except BallotError as exc:
            return self._problem(exc, request)
        return xlsx_response(sheets.template_workbook(), filename="Номинанты — шаблон.xlsx")


class BallotNomineeImportView(_StaffView):
    """``POST`` a filled-in .xlsx — as a preview, or for real."""

    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_import_nominees",
        summary="Import nominees from a spreadsheet",
        description=(
            "Send `dryRun=true` first: the response says exactly what would be added and which rows are "
            "wrong, with the row numbers Excel shows. Importing without previewing is how 150 rows of "
            "somebody else's formatting end up being removed by hand."
        ),
        parameters=[OpenApiParameter(name="dryRun", required=False, type=bool)],
        request=None,
        responses={200: ImportPreviewSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, ballot_id: str) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            return self._problem(InvalidBallotDataError("Приложите файл .xlsx со списком номинантов."), request)

        try:
            parsed = self._owned(request, ballot_id)
        except BallotError as exc:
            return self._problem(exc, request)

        try:
            rows, sheet = sheets.read_nominees(upload)
        except SheetReadError as exc:
            return problem_response(
                status=400,
                type_suffix="bad-request",
                title="Bad request",
                detail=str(exc),
                instance=request.get_full_path(),
                request=request,
            )

        dry_run = str(request.query_params.get("dryRun", "")).lower() in {"1", "true", "yes"}
        try:
            preview = build_ballot_service().import_nominees(
                ImportNomineesCommand(
                    ballot_id=str(parsed),
                    rows=rows,
                    dry_run=dry_run,
                    rejected=tuple((error.row, error.message) for error in sheet.errors),
                )
            )
        except BallotError as exc:
            return self._problem(exc, request)

        payload = resources.import_preview(preview)
        payload["missingColumns"] = list(sheet.missing_columns)
        return envelope(payload, request)


class BallotResultsView(_StaffView):
    """``GET`` the finished vote as an .xlsx, ranked."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_export_results",
        summary="Download the results",
        request=None,
        responses={200: OpenApiResponse(description="An .xlsx ranked by votes.")},
    )
    def get(self, request: Request, ballot_id: str) -> HttpResponseBase:
        try:
            detail = build_ballot_service().get(self._owned(request, ballot_id))
        except BallotError as exc:
            return self._problem(exc, request)
        return xlsx_response(sheets.results_workbook(detail), filename=f"{detail.title} — итоги.xlsx")


class BallotQrView(_StaffView):
    """``GET`` the QR code that goes on the poster."""

    @extend_schema(
        tags=[_TAG],
        operation_id="voting_ballot_qr",
        summary="Download the ballot's QR code",
        request=None,
        responses={200: OpenApiResponse(description="A PNG of the public voting link.")},
    )
    def get(self, request: Request, ballot_id: str) -> HttpResponseBase:
        try:
            detail = build_ballot_service().get(self._owned(request, ballot_id))
        except BallotError as exc:
            return self._problem(exc, request)

        url = request.build_absolute_uri(f"/vote/{detail.slug}")
        image = qrcode.make(url)
        payload = io.BytesIO()
        image.save(payload, format="PNG")
        response = HttpResponse(payload.getvalue(), content_type="image/png")
        response["Content-Disposition"] = f'attachment; filename="qr-{detail.slug}.png"'
        return response


def _nominee_row(payload: dict[str, Any]) -> NomineeRow:
    return NomineeRow(
        title=str(payload.get("title", "")),
        subtitle=str(payload.get("subtitle") or ""),
        city=str(payload.get("city") or ""),
        photo=payload.get("photo") or None,
        number=payload.get("number"),
    )
