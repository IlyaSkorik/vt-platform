"""Organizer and jury routes for the Judging bounded context.

Mounted under ``/api/v1/`` (ARCH-001 §14, API-000 §2). Two prefixes, and the split is
the same one the views make: ``staff/judging/`` is the organizer's, ``jury/`` is the
panel's. The board has its own unauthenticated router
(:mod:`apps.judging.presentation.public_urls`).
"""

from __future__ import annotations

from django.urls import path

from .views import (
    JudgingAwardScaleView,
    JudgingBoardSettingsView,
    JudgingCriteriaView,
    JudgingScoringRulesView,
    JudgingSetupView,
    JudgingTallyApplyView,
    JudgingTallyScopeView,
    JudgingTallyView,
    JuryAssignmentsView,
    JuryCollectionView,
    JuryDetailView,
    JuryInvitationAcceptView,
    JuryMemberReinviteView,
    JuryMemberRevokeView,
    JuryScorecardView,
    JuryTaskListView,
    ScoringCloseView,
    ScoringOpenView,
    ScoringStateListView,
)

app_name = "judging"

urlpatterns = [
    # The organizer's «Судейство» section.
    path("staff/judging/setup", JudgingSetupView.as_view(), name="setup"),
    path("staff/judging/criteria", JudgingCriteriaView.as_view(), name="criteria"),
    path("staff/judging/award-scale", JudgingAwardScaleView.as_view(), name="award-scale"),
    path("staff/judging/scoring-rules", JudgingScoringRulesView.as_view(), name="scoring-rules"),
    path("staff/judging/tally-scope", JudgingTallyScopeView.as_view(), name="tally-scope"),
    path("staff/judging/board", JudgingBoardSettingsView.as_view(), name="board-settings"),
    # The panel.
    path("staff/judging/jury", JuryCollectionView.as_view(), name="jury"),
    path("staff/judging/jury/<str:member_id>", JuryDetailView.as_view(), name="jury-detail"),
    path("staff/judging/jury/<str:member_id>/assignments", JuryAssignmentsView.as_view(), name="jury-assignments"),
    path("staff/judging/jury/<str:member_id>/reinvite", JuryMemberReinviteView.as_view(), name="jury-reinvite"),
    path("staff/judging/jury/<str:member_id>/revoke", JuryMemberRevokeView.as_view(), name="jury-revoke"),
    # The day itself.
    path("staff/judging/scoring", ScoringStateListView.as_view(), name="scoring-states"),
    path("staff/judging/scoring/open", ScoringOpenView.as_view(), name="scoring-open"),
    path("staff/judging/scoring/close", ScoringCloseView.as_view(), name="scoring-close"),
    path("staff/judging/tally", JudgingTallyView.as_view(), name="tally"),
    path("staff/judging/tally/apply", JudgingTallyApplyView.as_view(), name="tally-apply"),
    # The judge's own endpoints — authenticated, never staff-gated.
    path("jury/tasks", JuryTaskListView.as_view(), name="jury-tasks"),
    path("jury/scorecards", JuryScorecardView.as_view(), name="jury-scorecards"),
    path("jury/invitations/<str:token>/accept", JuryInvitationAcceptView.as_view(), name="jury-invitation-accept"),
]
