"""Command DTOs for the Voting application layer.

Flat, primitive-only inputs (ARCH-001 §7.3): strings, ints and ``None``. Parsing
them into value objects is the service's first act, so a malformed request fails
in one place with one vocabulary of errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    "AddNomineeCommand",
    "CastVoteCommand",
    "CreateBallotCommand",
    "EditNomineeCommand",
    "ImportNomineesCommand",
    "NomineeRow",
    "ReorderNomineesCommand",
    "SeedFromProgramCommand",
    "UpdateBallotCommand",
]


@dataclass(frozen=True, slots=True)
class CreateBallotCommand:
    """Start a ballot.

    ``competition_id`` is optional and that is the point: a festival that has not
    moved onto the platform gets exactly the same ballot as one that has.
    """

    organization_id: str
    title: str
    competition_id: str | None = None
    description: str = ""
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    votes_per_voter: int = 1
    cooldown_hours: int = 0
    reveal: str = "AFTER_CLOSE"


@dataclass(frozen=True, slots=True)
class UpdateBallotCommand:
    """Change a ballot's wording or its rules. Absent fields are left alone."""

    ballot_id: str
    title: str | None = None
    description: str | None = None
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    # Whether the window fields above are meaningful. Without this, "clear the
    # closing time" and "do not touch the closing time" are the same payload.
    window_given: bool = False
    votes_per_voter: int | None = None
    cooldown_hours: int | None = None
    reveal: str | None = None


@dataclass(frozen=True, slots=True)
class NomineeRow:
    """One nominee as it arrives from a form, a spreadsheet or a programme."""

    title: str
    subtitle: str = ""
    city: str = ""
    photo: str | None = None
    number: int | None = None
    submission_id: str | None = None
    program_item_id: str | None = None


@dataclass(frozen=True, slots=True)
class AddNomineeCommand:
    """Put one more nominee on the ballot."""

    ballot_id: str
    nominee: NomineeRow


@dataclass(frozen=True, slots=True)
class EditNomineeCommand:
    """Correct a nominee's card. Absent fields are left alone."""

    ballot_id: str
    nominee_id: str
    title: str | None = None
    subtitle: str | None = None
    city: str | None = None
    photo: str | None = None
    number: int | None = None


@dataclass(frozen=True, slots=True)
class ReorderNomineesCommand:
    """Rearrange the list. ``order`` must name every nominee exactly once."""

    ballot_id: str
    order: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ImportNomineesCommand:
    """Add a batch of nominees read from a spreadsheet.

    ``dry_run`` returns what *would* happen without writing anything. An import
    that silently pours 150 rows of somebody else's formatting into an open ballot
    is an import that gets undone by hand.
    """

    ballot_id: str
    rows: tuple[NomineeRow, ...] = field(default_factory=tuple)
    dry_run: bool = False
    #: Rows the reader could not use, carried through so the preview can show them
    #: alongside the good ones instead of in a separate place.
    rejected: tuple[tuple[int, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SeedFromProgramCommand:
    """Fill the list from a programme of the festival this ballot belongs to."""

    ballot_id: str
    program_id: str


@dataclass(frozen=True, slots=True)
class CastVoteCommand:
    """One person's votes, as submitted from the public page.

    A list rather than a single id because a ballot may allow several: sending them
    together lets the whole submission be accepted or refused as one, instead of
    leaving somebody with two of their three votes spent and an error on screen.
    """

    slug: str
    nominee_ids: tuple[str, ...] = field(default_factory=tuple)
