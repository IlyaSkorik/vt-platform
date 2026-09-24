"""Organizer and jury REST edge for the Judging bounded context.

Thin adapters over :mod:`apps.judging.application.services`: parse, delegate, render.

Three audiences, three base classes, and the split is the security boundary:

* :class:`_StaffView` — the organizer. Staff membership plus the ``JURY`` module.
* :class:`_JuryView` — a judge. Authenticated and **not** staff-gated: a jury member is
  a guest of the organization, not an employee of it. What they may touch is decided by
  the seat the service looks up from their account, never by an id in the request.
* the board is public and lives in :mod:`.public_views`.

Every configuration write answers with the *whole* setup, the way the protocols edge
answers with the whole protocol: editing a criterion changes whether the scale can
still decide an award and whether the screen should warn about it, and a client that
renders the response is never showing a stale screen.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.judging.application.commands import (
    AssignJuryMemberCommand,
    CloseScoringCommand,
    InviteJuryMemberCommand,
    OpenScoringCommand,
    SubmitScorecardCommand,
    UpdateAwardScaleCommand,
    UpdateBoardCommand,
    UpdateCriteriaCommand,
    UpdateJuryMemberCommand,
    UpdateScoringRulesCommand,
    UpdateTallyScopeCommand,
)
from apps.judging.composition import build_judging_configuration_service, build_scoring_service
from apps.judging.domain.exceptions import JudgingError
from apps.judging.presentation.api.v1 import problems
from apps.judging.presentation.api.v1.rendering import (
    jury_member_json,
    scoring_state_json,
    setup_json,
    tally_json,
    task_json,
)
from apps.judging.presentation.api.v1.serializers import (
    AssignJuryRequestSerializer,
    AwardScaleRequestSerializer,
    BoardRequestSerializer,
    CriteriaRequestSerializer,
    InviteJuryRequestSerializer,
    JudgingProblemDetailSerializer,
    JudgingSetupEnvelopeSerializer,
    JuryListEnvelopeSerializer,
    JuryMemberEnvelopeSerializer,
    JuryTaskEnvelopeSerializer,
    JuryTaskListEnvelopeSerializer,
    ScoringRulesRequestSerializer,
    ScoringStateEnvelopeSerializer,
    ScoringStateListEnvelopeSerializer,
    ScoringStateRequestSerializer,
    SubmitScorecardRequestSerializer,
    TallyEnvelopeSerializer,
    TallyScopeRequestSerializer,
    UpdateJuryRequestSerializer,
)
from apps.organization.domain.value_objects import OrganizationModule
from apps.organization.presentation.permissions import IsModuleEnabled, IsOrganizationStaff

_TAG = "Judging"
_JURY_TAG = "Jury"

__all__ = [
    "JudgingAwardScaleView",
    "JudgingBoardSettingsView",
    "JudgingCriteriaView",
    "JudgingScoringRulesView",
    "JudgingSetupView",
    "JudgingTallyApplyView",
    "JudgingTallyScopeView",
    "JudgingTallyView",
    "JuryAssignmentsView",
    "JuryCollectionView",
    "JuryDetailView",
    "JuryInvitationAcceptView",
    "JuryMemberReinviteView",
    "JuryMemberRevokeView",
    "JuryScorecardView",
    "JuryTaskListView",
    "ScoringCloseView",
    "ScoringOpenView",
    "ScoringStateListView",
]

_PROBLEM_RESPONSES = {
    400: OpenApiResponse(JudgingProblemDetailSerializer, description="Malformed."),
    404: OpenApiResponse(JudgingProblemDetailSerializer, description="Not found."),
    409: OpenApiResponse(JudgingProblemDetailSerializer, description="Conflict."),
    422: OpenApiResponse(JudgingProblemDetailSerializer, description="Unprocessable."),
}

_COMPETITION_PARAM = OpenApiParameter("competitionId", str, required=True, description="The competition being judged.")


class _JudgingView(APIView):
    """Shared error rendering and query-parameter handling."""

    def _problem(self, exc: JudgingError, request: Request) -> Response:
        return problems.judging_problem(exc, instance=request.get_full_path(), request=request)

    def _require_competition(self, request: Request) -> tuple[str | None, Response | None]:
        competition_id = request.query_params.get("competitionId")
        if not competition_id:
            return None, problems.validation_problem(
                {"competitionId": ["This query parameter is required."]},
                instance=request.get_full_path(),
                request=request,
            )
        return competition_id, None


class _StaffView(_JudgingView):
    """Authenticated organization staff, on a festival with the jury module."""

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff, IsModuleEnabled.of(OrganizationModule.JURY))


class _JuryView(_JudgingView):
    """An authenticated account that may hold a seat on some festival's panel.

    Deliberately not staff-gated. A jury member is invited to a festival, not employed
    by the organization running it, and requiring staff membership would mean handing
    every guest judge a key to the applications, the money and the participants.

    Authorization happens one layer down instead: the service resolves the caller's
    account to a seat and refuses everything when there is not one.
    """

    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def _user_id(request: Request) -> str:
        return str(getattr(request.user, "id", ""))


# ---------------------------------------------------------------------------
# The organizer's «Судейство» section
# ---------------------------------------------------------------------------


class JudgingSetupView(_StaffView):
    """``GET /api/v1/staff/judging/setup`` — the whole configuration screen."""

    @extend_schema(
        tags=[_TAG],
        operation_id="judgingSetupRead",
        parameters=[_COMPETITION_PARAM],
        responses={200: JudgingSetupEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        competition_id, failure = self._require_competition(request)
        if failure is not None:
            return failure
        try:
            view = build_judging_configuration_service().setup(str(competition_id))
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, setup_json(view))


class JudgingCriteriaView(_StaffView):
    """``PUT /api/v1/staff/judging/criteria`` — replace one sheet of criteria."""

    @extend_schema(
        tags=[_TAG],
        operation_id="judgingCriteriaReplace",
        request=CriteriaRequestSerializer,
        responses={200: JudgingSetupEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request) -> Response:
        serializer = CriteriaRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = UpdateCriteriaCommand(
            competition_id=str(data["competitionId"]),
            scope=str(data["scope"]),
            target_id=str(data["targetId"]),
            criteria=[_criterion_payload(item) for item in data["criteria"]],
        )
        try:
            view = build_judging_configuration_service().update_criteria(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, setup_json(view))


class JudgingAwardScaleView(_StaffView):
    """``PUT /api/v1/staff/judging/award-scale`` — replace the festival's award scale."""

    @extend_schema(
        tags=[_TAG],
        operation_id="judgingAwardScaleReplace",
        request=AwardScaleRequestSerializer,
        responses={200: JudgingSetupEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request) -> Response:
        serializer = AwardScaleRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = UpdateAwardScaleCommand(
            competition_id=str(data["competitionId"]),
            tiers=[_tier_payload(item) for item in data["tiers"]],
        )
        try:
            view = build_judging_configuration_service().update_award_scale(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, setup_json(view))


class JudgingScoringRulesView(_StaffView):
    """``PUT /api/v1/staff/judging/scoring-rules`` — how sheets become one number."""

    @extend_schema(
        tags=[_TAG],
        operation_id="judgingScoringRulesUpdate",
        request=ScoringRulesRequestSerializer,
        responses={200: JudgingSetupEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request) -> Response:
        serializer = ScoringRulesRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = UpdateScoringRulesCommand(
            competition_id=str(data["competitionId"]),
            aggregation=str(data["aggregation"]),
            drop_highest=bool(data.get("dropHighest", False)),
            drop_lowest=bool(data.get("dropLowest", False)),
        )
        try:
            view = build_judging_configuration_service().update_scoring_rules(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, setup_json(view))


class JudgingTallyScopeView(_StaffView):
    """``PUT /api/v1/staff/judging/tally-scope`` — the axes results are announced by."""

    @extend_schema(
        tags=[_TAG],
        operation_id="judgingTallyScopeUpdate",
        request=TallyScopeRequestSerializer,
        responses={200: JudgingSetupEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request) -> Response:
        serializer = TallyScopeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = UpdateTallyScopeCommand(
            competition_id=str(data["competitionId"]),
            dimensions=[str(item) for item in data["dimensions"]],
        )
        try:
            view = build_judging_configuration_service().update_tally_scope(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, setup_json(view))


class JudgingBoardSettingsView(_StaffView):
    """``PUT /api/v1/staff/judging/board`` — what the hall's screen shows, and when."""

    @extend_schema(
        tags=[_TAG],
        operation_id="judgingBoardUpdate",
        request=BoardRequestSerializer,
        responses={200: JudgingSetupEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request) -> Response:
        serializer = BoardRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = UpdateBoardCommand(
            competition_id=str(data["competitionId"]),
            enabled=bool(data["enabled"]),
            visibility=str(data["visibility"]),
            reveal=str(data["reveal"]),
            show_award=bool(data.get("showAward", True)),
            show_running_order=bool(data.get("showRunningOrder", True)),
        )
        try:
            view = build_judging_configuration_service().update_board(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, setup_json(view))


# ---------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------


class JuryCollectionView(_StaffView):
    """``GET /api/v1/staff/judging/jury`` — the panel; ``POST`` — seat somebody."""

    @extend_schema(
        tags=[_TAG],
        operation_id="juryList",
        parameters=[_COMPETITION_PARAM],
        responses={200: JuryListEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        competition_id, failure = self._require_competition(request)
        if failure is not None:
            return failure
        try:
            members = build_judging_configuration_service().jury(str(competition_id))
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, [jury_member_json(item) for item in members], meta={"total": len(members)})

    @extend_schema(
        tags=[_TAG],
        operation_id="juryInvite",
        request=InviteJuryRequestSerializer,
        responses={201: JuryMemberEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request) -> Response:
        serializer = InviteJuryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = InviteJuryMemberCommand(
            competition_id=str(data["competitionId"]),
            full_name=str(data["fullName"]),
            email=str(data["email"]),
            title=_optional(data.get("title")),
            is_chair=bool(data.get("isChair", False)),
            category_ids=[str(item) for item in data.get("categoryIds") or ()],
        )
        try:
            member = build_judging_configuration_service().invite(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, jury_member_json(member), status=201)


class JuryDetailView(_StaffView):
    """``PATCH`` — correct a seat; ``DELETE`` — take it off the panel."""

    @extend_schema(
        tags=[_TAG],
        operation_id="juryUpdate",
        request=UpdateJuryRequestSerializer,
        responses={200: JuryMemberEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def patch(self, request: Request, member_id: str) -> Response:
        serializer = UpdateJuryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = UpdateJuryMemberCommand(
            member_id=member_id,
            full_name=str(data["fullName"]),
            email=str(data["email"]),
            title=_optional(data.get("title")),
            is_chair=bool(data.get("isChair", False)),
        )
        try:
            member = build_judging_configuration_service().update_member(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, jury_member_json(member))

    @extend_schema(tags=[_TAG], operation_id="juryRemove", responses={204: None, **_PROBLEM_RESPONSES})
    def delete(self, request: Request, member_id: str) -> Response:
        try:
            build_judging_configuration_service().remove(member_id)
        except JudgingError as exc:
            return self._problem(exc, request)
        return Response(status=204)


class JuryAssignmentsView(_StaffView):
    """``PUT`` — replace the genres one member judges."""

    @extend_schema(
        tags=[_TAG],
        operation_id="juryAssign",
        request=AssignJuryRequestSerializer,
        responses={200: JuryMemberEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request, member_id: str) -> Response:
        serializer = AssignJuryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        command = AssignJuryMemberCommand(
            member_id=member_id,
            category_ids=[str(item) for item in serializer.validated_data["categoryIds"]],
        )
        try:
            member = build_judging_configuration_service().assign(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, jury_member_json(member))


class JuryMemberReinviteView(_StaffView):
    """``POST`` — issue a fresh link, invalidating the one already sent."""

    @extend_schema(tags=[_TAG], operation_id="juryReinvite", request=None, responses={200: JuryMemberEnvelopeSerializer, **_PROBLEM_RESPONSES})
    def post(self, request: Request, member_id: str) -> Response:
        try:
            member = build_judging_configuration_service().reinvite(member_id)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, jury_member_json(member))


class JuryMemberRevokeView(_StaffView):
    """``POST`` — withdraw the seat, leaving every mark it gave in place."""

    @extend_schema(tags=[_TAG], operation_id="juryRevoke", request=None, responses={200: JuryMemberEnvelopeSerializer, **_PROBLEM_RESPONSES})
    def post(self, request: Request, member_id: str) -> Response:
        try:
            member = build_judging_configuration_service().revoke(member_id)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, jury_member_json(member))


# ---------------------------------------------------------------------------
# The day itself
# ---------------------------------------------------------------------------


class ScoringOpenView(_StaffView):
    """``POST /api/v1/staff/judging/scoring/open`` — the host puts an act on stage."""

    @extend_schema(
        tags=[_TAG],
        operation_id="scoringOpen",
        request=ScoringStateRequestSerializer,
        responses={200: ScoringStateEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request) -> Response:
        serializer = ScoringStateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = OpenScoringCommand(
            competition_id=str(data["competitionId"]),
            submission_id=str(data["submissionId"]),
            close_previous=bool(data.get("closePrevious", True)),
        )
        try:
            state = build_scoring_service().open_scoring(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, scoring_state_json(state))


class ScoringCloseView(_StaffView):
    """``POST /api/v1/staff/judging/scoring/close`` — the host closes an act."""

    @extend_schema(
        tags=[_TAG],
        operation_id="scoringClose",
        request=ScoringStateRequestSerializer,
        responses={200: ScoringStateEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request) -> Response:
        serializer = ScoringStateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = CloseScoringCommand(competition_id=str(data["competitionId"]), submission_id=str(data["submissionId"]))
        try:
            state = build_scoring_service().close_scoring(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, scoring_state_json(state))


class ScoringStateListView(_StaffView):
    """``GET /api/v1/staff/judging/scoring`` — every act's state, for the host's screen."""

    @extend_schema(
        tags=[_TAG],
        operation_id="scoringStates",
        parameters=[_COMPETITION_PARAM],
        responses={200: ScoringStateListEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        competition_id, failure = self._require_competition(request)
        if failure is not None:
            return failure
        try:
            states = build_scoring_service().states(str(competition_id))
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, [scoring_state_json(item) for item in states], meta={"total": len(states)})


class JudgingTallyView(_StaffView):
    """``GET /api/v1/staff/judging/tally`` — every act reckoned, grouped and awarded."""

    @extend_schema(
        tags=[_TAG],
        operation_id="judgingTally",
        parameters=[_COMPETITION_PARAM],
        responses={200: TallyEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        competition_id, failure = self._require_competition(request)
        if failure is not None:
            return failure
        try:
            view = build_scoring_service().tally(str(competition_id))
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, tally_json(view))


class JudgingTallyApplyView(_StaffView):
    """``POST /api/v1/staff/judging/tally/apply`` — write the results into the protocols.

    Answers with how many rows changed rather than with the protocols themselves: the
    protocols tab is a different screen with its own cache, and returning a dozen
    documents to a button that lives elsewhere would be a payload nobody renders.
    """

    @extend_schema(
        tags=[_TAG],
        operation_id="judgingTallyApply",
        request=None,
        parameters=[_COMPETITION_PARAM],
        responses={
            200: OpenApiResponse(description="How many protocol rows were changed."),
            **_PROBLEM_RESPONSES,
        },
    )
    def post(self, request: Request) -> Response:
        competition_id, failure = self._require_competition(request)
        if failure is not None:
            return failure
        try:
            changed = build_scoring_service().apply_to_protocols(str(competition_id))
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, {"rowsChanged": changed})


# ---------------------------------------------------------------------------
# The judge's tablet
# ---------------------------------------------------------------------------


class JuryTaskListView(_JuryView):
    """``GET /api/v1/jury/tasks`` — the acts this judge is seated for."""

    @extend_schema(
        tags=[_JURY_TAG],
        operation_id="juryTasks",
        parameters=[_COMPETITION_PARAM],
        responses={200: JuryTaskListEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def get(self, request: Request) -> Response:
        competition_id, failure = self._require_competition(request)
        if failure is not None:
            return failure
        try:
            tasks = build_scoring_service().tasks_for_judge(competition_id=str(competition_id), user_id=self._user_id(request))
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, [task_json(item) for item in tasks], meta={"total": len(tasks)})


class JuryScorecardView(_JuryView):
    """``PUT /api/v1/jury/scorecards`` — send a sheet, or correct the one already sent.

    ``PUT`` rather than ``POST`` because that is what it is: the sheet is replaced
    wholesale and sending the same body twice leaves the same marks, which is exactly
    what a tablet retrying after a dropped connection needs.
    """

    @extend_schema(
        tags=[_JURY_TAG],
        operation_id="juryScorecardSubmit",
        request=SubmitScorecardRequestSerializer,
        responses={200: JuryTaskEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def put(self, request: Request) -> Response:
        serializer = SubmitScorecardRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.get_full_path(), request=request)
        data = serializer.validated_data
        command = SubmitScorecardCommand(
            competition_id=str(data["competitionId"]),
            submission_id=str(data["submissionId"]),
            user_id=self._user_id(request),
            scores={str(key): value for key, value in data["scores"].items()},
            comment=_optional(data.get("comment")),
        )
        try:
            task = build_scoring_service().submit_scorecard(command)
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, task_json(task))


class JuryInvitationAcceptView(_JuryView):
    """``POST /api/v1/jury/invitations/<token>/accept`` — attach the caller's account.

    Authenticated on purpose: the link's job is to identify the *seat*, and the signed-in
    account is what identifies the *person*. A judge who follows the link while logged
    out registers or signs in first, and lands back here.
    """

    @extend_schema(
        tags=[_JURY_TAG],
        operation_id="juryInvitationAccept",
        request=None,
        responses={200: JuryMemberEnvelopeSerializer, **_PROBLEM_RESPONSES},
    )
    def post(self, request: Request, token: str) -> Response:
        try:
            member = build_judging_configuration_service().accept_invitation(token=token, user_id=self._user_id(request))
        except JudgingError as exc:
            return self._problem(exc, request)
        return problems.envelope(request, jury_member_json(member))


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def _optional(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _criterion_payload(item: dict[str, Any]) -> dict[str, object]:
    return {
        "id": str(item["id"]) if item.get("id") else None,
        "name": item["name"],
        "maxScore": item["maxScore"],
        "weight": item["weight"],
        "sortOrder": item.get("sortOrder", 0),
        "description": item.get("description"),
    }


def _tier_payload(item: dict[str, Any]) -> dict[str, object]:
    return {
        "code": item.get("code") or "",
        "label": item["label"],
        "minScore": item.get("minScore"),
        "maxScore": item.get("maxScore"),
        "sortOrder": item.get("sortOrder", 0),
    }
