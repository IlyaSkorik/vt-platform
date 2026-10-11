"""Command DTOs for the Programs use cases.

Framework-neutral input shapes: primitives only, so a DRF view, a management
command or a test constructs them the same way. ``None`` consistently means "leave
this as it is" on the update commands, which is what lets one endpoint carry a
partial edit without a sentinel type.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "AddBlockCommand",
    "AddColumnCommand",
    "AddPerformanceCommand",
    "AnnounceProgramCommand",
    "ArrangeProgramCommand",
    "ArrangementPayload",
    "CreateProgramCommand",
    "CreateShareCommand",
    "EditItemCommand",
    "FillCellsCommand",
    "HostReorderCommand",
    "RenameColumnCommand",
    "ReorderItemsCommand",
    "SetItemProgressCommand",
    "UpdateProgramCommand",
    "UpdateShareCommand",
]


@dataclass(frozen=True, slots=True)
class ArrangementPayload:
    """The rules an organizer filled a generation form in with.

    Primitives throughout, exactly as the settings screen sends them; the service turns
    them into the domain's :class:`~apps.programs.domain.value_objects.ArrangementSettings`
    and lets the value objects do the rejecting.

    Every field is optional and falls back to the domain default, so a form that offers
    three knobs today and five tomorrow needs no change here. A *break* is the one place
    two fields travel together: a rule that fires needs something to insert, and the
    domain refuses a rule without its block.
    """

    grouping: tuple[str, ...] | None = None
    order_within_group: str | None = None
    break_rule: str | None = None
    break_after_seconds: int | None = None
    break_after_items: int | None = None
    break_title: str | None = None
    break_duration_seconds: int | None = None
    repeat_gap: int | None = None
    opening_title: str | None = None
    opening_duration_seconds: int | None = None
    award_title: str | None = None
    award_duration_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class ArrangeProgramCommand:
    """Generate the whole running order of one programme from a set of rules.

    ``settings`` of ``None`` means "the rules this programme was last generated from",
    falling back to the defaults for one that never was - which is what makes
    "пересобрать" a button with no form behind it. A payload that *is* present is read
    as complete: an omitted field takes the domain default rather than whatever was
    saved, so what the organizer sees on the form is what they get.
    """

    program_id: str
    settings: ArrangementPayload | None = None


@dataclass(frozen=True, slots=True)
class CreateProgramCommand:
    """Start a new, empty program for a competition (usually for one nomination)."""

    competition_id: str
    name: str
    nomination_id: str | None = None
    buffer_seconds: int = 0
    starts_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class UpdateProgramCommand:
    """Change a program's name, buffer or start time.

    ``clear_starts_at`` exists because ``starts_at=None`` already means "unchanged";
    dropping a start time is a deliberate act and says so explicitly.
    """

    program_id: str
    name: str | None = None
    buffer_seconds: int | None = None
    starts_at: datetime | None = None
    clear_starts_at: bool = False


@dataclass(frozen=True, slots=True)
class AddPerformanceCommand:
    """Give one competing act a slot.

    ``duration_seconds`` overrides the act's declared length for this slot only;
    without it the slot is seeded from the act itself.
    """

    program_id: str
    submission_id: str
    position: int | None = None
    duration_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class AddBlockCommand:
    """Insert a standalone block - a break today, an opening or an award later."""

    program_id: str
    title: str
    duration_seconds: int
    kind: str = "BREAK"
    position: int | None = None


@dataclass(frozen=True, slots=True)
class EditItemCommand:
    """Retitle and/or resize one existing slot."""

    program_id: str
    item_id: str
    title: str | None = None
    duration_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class ReorderItemsCommand:
    """Replace the running order with the given one (a full permutation)."""

    program_id: str
    item_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CreateShareCommand:
    """Publish a named edition of the program behind a fresh public slug.

    ``columns`` is the selection that defines the edition - which columns of the table
    its reader sees. Empty means the default columns.

    An empty ``item_ids`` publishes every row and keeps following the program.
    """

    program_id: str
    name: str
    columns: tuple[str, ...] = ()
    item_ids: tuple[str, ...] = ()
    #: Make this the host's edition: its holder may drive the running order on the day.
    controls_running_order: bool = False


@dataclass(frozen=True, slots=True)
class AnnounceProgramCommand:
    """Tell everyone in a published edition that it is up, and where to read it.

    Named by the **edition**, not by the programme: a programme can have several links
    cut to different columns - one for the hall screen, one for the sound desk - and the
    one participants should be sent is a choice only the organizer can make. It also
    decides who is written to: an edition published over a slice of the running order is
    announced to that slice.
    """

    program_id: str
    share_id: str
    #: A line of the organizer's own above the running order ("сбор за час до начала").
    note: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateShareCommand:
    """Rename a published edition, re-column it, or change what it may control.

    Its slug is permanent, so a link already handed out keeps working.
    """

    program_id: str
    share_id: str
    name: str | None = None
    columns: tuple[str, ...] | None = None
    controls_running_order: bool | None = None


@dataclass(frozen=True, slots=True)
class AddColumnCommand:
    """Add a column of the organizer's own ("Микрофон", "Реквизит")."""

    program_id: str
    title: str


@dataclass(frozen=True, slots=True)
class RenameColumnCommand:
    """Rename a custom column, keeping every value already filled into it."""

    program_id: str
    column_id: str
    title: str


@dataclass(frozen=True, slots=True)
class FillCellsCommand:
    """Write hand-filled values for one slot, keyed by custom column key.

    A blank value clears the cell, which is how a value is removed without a second verb.
    """

    program_id: str
    item_id: str
    values: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class SetItemProgressCommand:
    """Mark how far one slot has got, as the host announces the day.

    ``slug`` identifies the host's own public link; it is the only credential involved,
    which is why it is granted per edition rather than per user.
    """

    slug: str
    item_id: str
    progress: str


@dataclass(frozen=True, slots=True)
class HostReorderCommand:
    """Rearrange the running order from the host's link, mid-event."""

    slug: str
    item_ids: tuple[str, ...]
