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
    "AddPerformanceCommand",
    "CreateProgramCommand",
    "CreateShareCommand",
    "EditItemCommand",
    "ReorderItemsCommand",
    "UpdateProgramCommand",
]


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

    An empty ``item_ids`` publishes the whole program and keeps following it.
    """

    program_id: str
    name: str
    item_ids: tuple[str, ...] = ()
