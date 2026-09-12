"""Result & view DTOs for the Voting application layer.

Immutable, primitive-only output shapes: ids as strings, instants as
:class:`~datetime.datetime`. They are the boundary in the outward direction, so no
outer layer needs the domain to read a ballot.

The organizer's view and the public one are deliberately **separate types** rather
than one type with fields blanked out. The public view is read by anyone holding a
link; keeping it its own shape is what stops an organizer-only field from leaking
into it by accident a year from now.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    "BallotDetailView",
    "BallotSummaryView",
    "ImportPreviewView",
    "NomineeView",
    "ProgramOptionView",
    "PublicBallotView",
    "PublicNomineeView",
    "VoteReceiptView",
]


@dataclass(frozen=True, slots=True)
class NomineeView:
    """One nominee as the organizer sees them — card, order and count."""

    id: str
    position: int
    title: str
    subtitle: str
    photo: str | None
    number: int | None
    withdrawn: bool
    votes: int
    submission_id: str | None = None
    program_item_id: str | None = None


@dataclass(frozen=True, slots=True)
class BallotSummaryView:
    """One row of the organizer's ballot list."""

    id: str
    title: str
    slug: str
    status: str
    competition_id: str | None
    standalone: bool
    nominees: int
    total_votes: int
    opens_at: datetime | None
    closes_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class BallotDetailView:
    """The whole ballot as the organizer edits it."""

    id: str
    title: str
    description: str
    slug: str
    status: str
    competition_id: str | None
    standalone: bool
    opens_at: datetime | None
    closes_at: datetime | None
    votes_per_voter: int
    cooldown_hours: int
    reveal: str
    nominees: tuple[NomineeView, ...] = field(default_factory=tuple)
    total_votes: int = 0
    #: Distinct people, not votes. On a ballot allowing three picks the two numbers
    #: differ by design, and an organizer reading only one of them draws the wrong
    #: conclusion about how many came.
    voters: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PublicNomineeView:
    """One nominee as the audience sees them.

    ``votes`` is ``None`` whenever the ballot's reveal policy says the count is not
    for the public yet — absent rather than zero, so a page cannot render "0" for
    something it merely is not allowed to know.
    """

    id: str
    position: int
    title: str
    subtitle: str
    photo: str | None
    number: int | None
    votes: int | None = None
    #: Whether this reader has already backed this nominee in the current window.
    chosen: bool = False


@dataclass(frozen=True, slots=True)
class PublicBallotView:
    """The voting page: the question, the options and what this reader may do."""

    title: str
    description: str
    slug: str
    status: str
    #: Whether a vote sent right now would be counted (window included).
    open: bool
    votes_per_voter: int
    #: How many of their votes this reader still has in the current window.
    votes_left: int
    reveal_totals: bool
    nominees: tuple[PublicNomineeView, ...] = field(default_factory=tuple)
    total_votes: int | None = None
    closes_at: datetime | None = None
    #: A short line explaining why voting is not possible, when it is not. Written
    #: for the person holding the phone, not for the developer.
    closed_reason: str | None = None


@dataclass(frozen=True, slots=True)
class VoteReceiptView:
    """What comes back the moment somebody votes.

    Carries the whole page state, so the client renders the result of the vote
    without a second request — and so a scoreboard the reader is allowed to see
    updates in the same breath.
    """

    ballot: PublicBallotView
    accepted: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ImportPreviewView:
    """What an import would do, or has just done.

    The same shape both ways on purpose: the preview an organizer agreed to is the
    report they get back, and a report assembled after the fact could only describe
    what happened rather than what was promised.
    """

    added: tuple[NomineeView, ...] = field(default_factory=tuple)
    #: ``(row number as Excel shows it, what is wrong with it)``.
    errors: tuple[tuple[int, str], ...] = field(default_factory=tuple)
    #: Declared columns the file did not have — reported so the interface can say
    #: "we ignored these" rather than dropping them in silence.
    missing_columns: tuple[str, ...] = field(default_factory=tuple)
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class ProgramOptionView:
    """One running order a ballot could be filled from.

    Only ever offered for a ballot that named a festival. ``nominees`` is how many
    acts it would contribute, so the organizer picks between "День 1" and "День 2"
    by what is in them rather than by name alone.
    """

    id: str
    name: str
    nominees: int
