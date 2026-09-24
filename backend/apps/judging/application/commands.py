"""Command objects for the Judging use cases.

Plain, frozen data (API-000 §7 maps them from camelCase at the edge). Every one carries
primitive values rather than domain types: the presentation layer parses JSON, and
turning a string into a :class:`~decimal.Decimal` or a :class:`uuid.UUID` is the
application layer's job, done once, where the error message can name the field.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "AssignJuryMemberCommand",
    "CloseScoringCommand",
    "InviteJuryMemberCommand",
    "OpenScoringCommand",
    "SubmitScorecardCommand",
    "UpdateAwardScaleCommand",
    "UpdateBoardCommand",
    "UpdateCriteriaCommand",
    "UpdateJuryMemberCommand",
    "UpdateScoringRulesCommand",
    "UpdateTallyScopeCommand",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateCriteriaCommand:
    """Replace one genre's or nomination's criteria sheet, wholesale.

    ``criteria`` entries carry ``id``, ``name``, ``maxScore``, ``weight``,
    ``sortOrder`` and an optional ``description``. An entry with no ``id`` is a new
    criterion and gets one; an existing id is kept, so a mark already given against it
    survives a rename.
    """

    competition_id: str
    scope: str
    target_id: str
    criteria: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class UpdateAwardScaleCommand:
    """Replace the festival's whole award scale.

    ``tiers`` entries carry ``code`` (optional — derived from the label when absent),
    ``label``, ``minScore``, ``maxScore`` and ``sortOrder``.
    """

    competition_id: str
    tiers: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class UpdateScoringRulesCommand:
    """Change how several judges' sheets become one number."""

    competition_id: str
    aggregation: str
    drop_highest: bool = False
    drop_lowest: bool = False


@dataclass(frozen=True, slots=True)
class UpdateTallyScopeCommand:
    """Change the axes results are reckoned and announced by."""

    competition_id: str
    dimensions: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class UpdateBoardCommand:
    """Change what the screen beside the stage shows, and when."""

    competition_id: str
    enabled: bool
    visibility: str
    reveal: str
    show_award: bool = True
    show_running_order: bool = True


# ---------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InviteJuryMemberCommand:
    """Seat somebody on the panel and send them a link."""

    competition_id: str
    full_name: str
    email: str
    title: str | None = None
    is_chair: bool = False
    category_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class UpdateJuryMemberCommand:
    """Correct a seat: the name, the regalia, the address, the chair."""

    member_id: str
    full_name: str
    email: str
    title: str | None = None
    is_chair: bool = False


@dataclass(frozen=True, slots=True)
class AssignJuryMemberCommand:
    """Replace the genres one member judges. An empty list means the whole festival."""

    member_id: str
    category_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# The day itself
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OpenScoringCommand:
    """The host put an act on stage."""

    competition_id: str
    submission_id: str
    #: Whether to close whatever was open. On by default because that is what a host
    #: pressing "следующий номер" means; a festival running two stages off one account
    #: turns it off and keeps both open.
    close_previous: bool = True


@dataclass(frozen=True, slots=True)
class CloseScoringCommand:
    """The host closed an act; marks freeze."""

    competition_id: str
    submission_id: str


@dataclass(frozen=True, slots=True)
class SubmitScorecardCommand:
    """One judge sending their sheet.

    ``scores`` maps criterion id to the mark given. The sheet is replaced wholesale, so
    a criterion left out of the mapping is a blank line and counts as zero — see
    :meth:`~apps.judging.domain.entities.Scorecard.total`.
    """

    competition_id: str
    submission_id: str
    #: The account sending it. The seat is looked up from this rather than trusted from
    #: the request, so a judge cannot submit as somebody else by changing an id.
    user_id: str
    scores: dict[str, object] = field(default_factory=dict)
    comment: str | None = None
