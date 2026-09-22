"""Command DTOs for the Finance bounded context.

Plain frozen dataclasses of primitives (ARCH-001 §7.3): the edge parses HTTP into
one of these, the service turns it into domain values. Nothing here validates — a
command that policed its own fields would be a second, quieter copy of the value
objects, and the two would drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

__all__ = ["AmendExpenseCommand", "RecordExpenseCommand"]


@dataclass(frozen=True, slots=True)
class RecordExpenseCommand:
    """One cost the operator is entering into the platform's books.

    ``organization_id`` absent means the cost belongs to the platform rather than
    to any one client — the ordinary case for hosting, and not a missing field.
    """

    amount: str
    category: str
    purpose: str
    spent_at: date
    organization_id: str | None = None
    note: str | None = None
    recorded_by: str | None = None


@dataclass(frozen=True, slots=True)
class AmendExpenseCommand:
    """A correction to a recorded expense: every field optional, ``None`` = unchanged.

    ``organization_id`` cannot express "move this off the client" that way, because
    ``None`` already means "do not touch it". ``reassign`` is what says the field
    was meant: with it set, ``organization_id`` is applied verbatim, ``None``
    included.
    """

    expense_id: str
    amount: str | None = None
    category: str | None = None
    purpose: str | None = None
    spent_at: date | None = None
    note: str | None = None
    organization_id: str | None = None
    reassign: bool = False
