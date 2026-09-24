"""Read models the Judging use cases hand back.

Flat, immutable, already-resolved values: names joined, labels looked up, arithmetic
done. A presentation layer renders these without reaching back for anything, which is
what keeps the REST edge a translation layer rather than a second place decisions get
made.

Three audiences are served here and they see deliberately different things:

* the **organizer** sees everything — the panel, each judge's mark, the comments;
* the **judge** sees their own sheet and the act, never another judge's mark and never
  a participant's name (ADR-0013);
* the **hall's board** sees whatever the organizer configured, and nothing else —
  which is why :class:`BoardView` is assembled by the service rather than filtered by a
  screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

__all__ = [
    "AwardTierView",
    "BoardEntryView",
    "BoardJudgeView",
    "BoardView",
    "CriteriaSetView",
    "CriterionView",
    "JudgeScoreView",
    "JudgingSetupView",
    "JuryMemberView",
    "JuryTaskView",
    "NominationView",
    "PerformanceTallyView",
    "ScorecardView",
    "ScoringStateView",
    "TallyGroupView",
    "TallySheetView",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CriterionView:
    id: str
    name: str
    max_score: Decimal
    weight: Decimal
    sort_order: int
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CriteriaSetView:
    scope: str
    target_id: str
    #: The genre's or nomination's name, so the screen lists sheets without a join.
    target_name: str | None
    criteria: tuple[CriterionView, ...]
    #: The most one judge can give under this sheet — the number an organizer sizes
    #: the award bands against.
    max_total: Decimal


@dataclass(frozen=True, slots=True)
class AwardTierView:
    code: str
    label: str
    min_score: Decimal | None
    max_score: Decimal | None
    sort_order: int


@dataclass(frozen=True, slots=True)
class NominationView:
    """One genre and its nominations, for the criteria screen's tree."""

    category_id: str
    name: str
    disciplines: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class JudgingSetupView:
    """The whole configuration screen in one payload."""

    competition_id: str
    online_judging: bool
    award_scale: tuple[AwardTierView, ...]
    criteria_sets: tuple[CriteriaSetView, ...]
    nominations: tuple[NominationView, ...]
    aggregation: str
    drop_highest: bool
    drop_lowest: bool
    tally_dimensions: tuple[str, ...]
    board_enabled: bool
    board_visibility: str
    board_reveal: str
    board_show_award: bool
    board_show_running_order: bool
    board_slug: str | None
    board_path: str | None
    jury_count: int
    #: Whether the scale can actually decide an award — i.e. any tier has a band. An
    #: online festival whose scale is unbanded will score everything and award nothing,
    #: and the screen says so before the day rather than after it.
    scale_is_banded: bool
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class JuryMemberView:
    id: str
    full_name: str
    email: str
    title: str | None
    status: str
    is_chair: bool
    #: Empty means the whole festival.
    category_ids: tuple[str, ...]
    category_names: tuple[str, ...]
    sort_order: int
    has_account: bool
    invited_at: datetime | None
    accepted_at: datetime | None
    #: The link to re-send, present only while an invitation is outstanding.
    invitation_path: str | None = None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScoringStateView:
    submission_id: str
    status: str
    opened_at: datetime | None
    closed_at: datetime | None


@dataclass(frozen=True, slots=True)
class JuryTaskView:
    """One act as its judge's tablet shows it.

    No participants and no teachers: the number, the act, where it competes. See the
    module docstring.
    """

    submission_id: str
    number: int
    title: str
    category_id: str
    category_name: str | None
    discipline_name: str | None
    age_category_name: str | None
    participation_format_name: str | None
    organization: str | None
    status: str
    criteria: tuple[CriterionView, ...]
    #: This judge's own marks, if they have sent any.
    my_scores: tuple[JudgeScoreView, ...]
    my_comment: str | None
    my_total: Decimal | None
    submitted_at: datetime | None
    #: Whether this judge may write right now: the act is open and they are seated for
    #: its genre.
    can_score: bool
    max_total: Decimal


@dataclass(frozen=True, slots=True)
class JudgeScoreView:
    criterion_id: str
    score: Decimal


@dataclass(frozen=True, slots=True)
class ScorecardView:
    """One judge's sheet as the organizer reads it."""

    jury_member_id: str
    jury_member_name: str
    scores: tuple[JudgeScoreView, ...]
    total: Decimal
    comment: str | None
    submitted_at: datetime | None
    submitted: bool


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PerformanceTallyView:
    submission_id: str
    number: int
    title: str
    organization: str | None
    score: Decimal | None
    max_score: Decimal
    award_code: str | None
    award_label: str | None
    submitted_count: int
    expected_judges: int
    status: str
    scorecards: tuple[ScorecardView, ...]


@dataclass(frozen=True, slots=True)
class TallyGroupView:
    """One sheet of results — the acts reckoned together, best first."""

    key: str
    heading: str
    category_id: str | None
    tallies: tuple[PerformanceTallyView, ...]


@dataclass(frozen=True, slots=True)
class TallySheetView:
    competition_id: str
    groups: tuple[TallyGroupView, ...]
    aggregation: str
    scale_is_banded: bool
    #: Acts that have a score but fall into no band — the organizer's warning list.
    unawarded_count: int


# ---------------------------------------------------------------------------
# The hall's board
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoardJudgeView:
    """One judge's mark as the hall sees it. Only rendered under ``PER_JUDGE``."""

    name: str
    total: Decimal | None


@dataclass(frozen=True, slots=True)
class BoardEntryView:
    number: int
    title: str
    organization: str | None
    category_name: str | None
    age_category_name: str | None
    status: str
    score: Decimal | None
    max_score: Decimal
    award_label: str | None
    submitted_count: int
    expected_judges: int
    judges: tuple[BoardJudgeView, ...]


@dataclass(frozen=True, slots=True)
class BoardView:
    """The screen beside the stage: what is on now, and what has already been marked."""

    competition_title: str
    visibility: str
    reveal: str
    show_award: bool
    current: BoardEntryView | None
    recent: tuple[BoardEntryView, ...]
