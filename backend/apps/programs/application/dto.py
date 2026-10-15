"""Result & view DTOs for the Programs application layer.

Immutable, primitive-only output shapes: ids and enums as strings, durations as
whole seconds, instants as :class:`~datetime.datetime`. They are the boundary in the
outward direction, so no outer layer needs the domain to read a program.

The organizer view and the public view are deliberately **separate shapes** rather
than one shape with fields blanked out. A public program is read by anyone holding a
link, and keeping its projection its own type is what stops an organizer-only field
from leaking into it by accident later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "AnnouncementView",
    "ArrangementView",
    "ColumnView",
    "ProgramDetailView",
    "ProgramItemView",
    "ProgramShareView",
    "ProgramSummaryView",
    "ProgramTableView",
    "PublicProgramRowView",
    "PublicProgramView",
    "SchedulePosition",
]


@dataclass(frozen=True, slots=True)
class ColumnView:
    """One column of the programme table: its stable key and its header.

    ``custom`` marks a column the organizer added themselves - the only ones that can be
    renamed, removed, or filled in by hand.
    """

    key: str
    label: str
    custom: bool = False


@dataclass(frozen=True, slots=True)
class SchedulePosition:
    """Where one item sits on the timeline.

    ``position`` is the row's place in the running order (1..N, always contiguous);
    :attr:`ProgramItemView.number` is the participant's permanent number, which does not
    change when the order does. The two are equal until somebody is moved.
    """

    position: int
    offset_seconds: int
    slot_seconds: int
    starts_at: datetime | None
    ends_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProgramItemView:
    """One slot as the organizer's constructor shows it.

    ``title`` is resolved: a block's own title, or the act's title for a performance
    slot. ``performance`` fields are ``None`` for blocks, and ``missing_performance``
    marks the one case an organizer must be able to see - a slot whose act has since
    been withdrawn from this competition.
    """

    id: str
    kind: str
    title: str
    #: The slot's number. Follows the running order until the programme is published, and
    #: is fixed to the slot from then on.
    number: int
    duration_seconds: int
    schedule: SchedulePosition
    submission_id: str | None = None
    participants: tuple[str, ...] = ()
    #: How many people stand on stage - a collective's own headcount, not the length of
    #: :attr:`participants`. ``0`` for a block, which puts nobody on stage.
    participant_count: int = 0
    teachers: tuple[str, ...] = ()
    #: Who to ring about this act: its teachers' phones, or the applicant's if none.
    contacts: tuple[str, ...] = ()
    nomination: str | None = None
    discipline: str | None = None
    age_category: str | None = None
    participant_group: str | None = None
    participation_format: str | None = None
    organization: str | None = None
    comment: str | None = None
    missing_performance: bool = False
    #: Hand-filled values, keyed by custom column key (``custom:<uuid>``).
    custom_values: tuple[tuple[str, str], ...] = ()
    #: How far this slot has got on the day (``PENDING`` until the host says otherwise).
    progress: str = "PENDING"


@dataclass(frozen=True, slots=True)
class AnnouncementView:
    """What came of announcing one published edition.

    Three numbers rather than one, because they answer three different questions and an
    organizer who sent 40 letters for 47 acts needs to know which gap they are looking
    at. ``skipped`` is acts whose applicant has no address to write to - the one failure
    mode that is nobody's mistake and cannot be retried into working.
    """

    #: Applicants written to. One letter each, however many acts they entered.
    notified: int
    #: Acts the edition covers and that are still entered in this competition.
    acts: int
    #: Acts whose applicant could not be written to.
    skipped: int


@dataclass(frozen=True, slots=True)
class ProgramShareView:
    """A public edition of the program, as listed in the constructor."""

    id: str
    name: str
    slug: str
    path: str
    columns: tuple[ColumnView, ...]
    item_count: int
    covers_whole_program: bool
    #: Whether this link may drive the running order on the day (the host's edition).
    controls_running_order: bool
    created_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProgramSummaryView:
    """A program as it appears in a list of programs."""

    id: str
    competition_id: str
    nomination_id: str | None
    name: str
    buffer_seconds: int
    starts_at: datetime | None
    item_count: int
    performance_count: int
    total_seconds: int
    share_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ArrangementView:
    """The rules a programme was last generated from, on their way back to the form.

    Flat and already stringified: the settings screen reopens on exactly what produced
    the running order on screen, so "пересобрать" and "пересобрать, но с перерывом"
    start from the same place.
    """

    grouping: tuple[str, ...]
    order_within_group: str
    break_rule: str
    break_after_seconds: int
    break_after_items: int
    break_title: str | None
    break_duration_seconds: int | None
    repeat_gap: int
    opening_title: str | None
    opening_duration_seconds: int | None
    award_title: str | None
    award_duration_seconds: int | None


@dataclass(frozen=True, slots=True)
class ProgramDetailView:
    """One program in full: its settings, its computed timetable, its public links."""

    id: str
    competition_id: str
    nomination_id: str | None
    name: str
    buffer_seconds: int
    starts_at: datetime | None
    items: tuple[ProgramItemView, ...]
    shares: tuple[ProgramShareView, ...]
    #: Every column the table can carry, in canonical order - what the constructor
    #: renders its header from and what a publish dialog offers to choose between.
    available_columns: tuple[ColumnView, ...]
    #: Whether numbers are fixed to their slots. ``False`` while the programme is being
    #: assembled: numbers then follow the order and a reorder renumbers freely.
    numbers_frozen: bool
    #: The first publication, i.e. when the numbers were fixed (``None`` if never).
    numbers_frozen_at: datetime | None
    total_seconds: int
    ends_at: datetime | None
    #: The generation rules this programme carries, or ``None`` if it was only ever
    #: built by hand. What the generator dialog prefills from.
    arrangement: ArrangementView | None
    created_at: datetime
    updated_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class ProgramTableView:
    """A programme as a plain table, for a renderer that knows nothing about programmes.

    The same shape the public screen is built from, minus anything link-specific: a heading,
    the chosen columns, and one row of already-rendered cells each. That is deliberately all
    a PDF (or a CSV, later) needs, which keeps the renderer a dumb table printer rather than
    a second place that knows what a programme is.
    """

    title: str
    subtitle: str | None
    starts_at: datetime | None
    total_seconds: int
    columns: tuple[ColumnView, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class ArchiveFileView:
    """One file of a programme archive, named for the slot it belongs to.

    ``filename`` is what the file is called inside the archive. Whoever collects the
    material works from the running order, so the number leads and everything else is
    there to confirm the right file is cued.
    """

    number: int
    filename: str
    reference: str


@dataclass(frozen=True, slots=True)
class ProgramArchiveView:
    """Every file of one kind in a programme, plus the slots that have none.

    ``missing`` is not an error: a live act needs no backing track, and plenty of acts
    bring no video. It is listed because the person collecting the material is the one
    who has to know which numbers to chase, and an archive that silently omits them looks
    complete when it is not.
    """

    title: str
    files: tuple[ArchiveFileView, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PublicProgramRowView:
    """One row of a public programme table.

    ``cells`` is aligned with the view's :attr:`PublicProgramView.columns` - a column the
    organizer did not publish produces no cell at all, so a hidden column cannot be read
    off the wire. ``kind`` is carried for styling (a break is drawn differently), not as
    data about the act.

    ``progress`` is what makes a screen live: the row on stage is highlighted and the ones
    behind it are greyed out. ``id`` is present **only** on the host's edition, because it
    is the handle their controls act on - a read-only link carries no ids at all.
    """

    kind: str
    cells: tuple[str, ...]
    progress: str = "PENDING"
    id: str | None = None


@dataclass(frozen=True, slots=True)
class PublicProgramView:
    """What a public link resolves to: a table, and the columns it was cut to."""

    name: str
    slug: str
    competition_title: str | None
    nomination: str | None
    starts_at: datetime | None
    total_seconds: int
    columns: tuple[ColumnView, ...]
    rows: tuple[PublicProgramRowView, ...]
    #: Whether the reader of this link may drive the running order (the host's edition).
    controls_running_order: bool = False
