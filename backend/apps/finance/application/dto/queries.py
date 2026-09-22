"""Read views returned by the Finance use cases.

Flat, framework-free projections (ARCH-001 §7.3) — the REST edge renders these and
never touches an aggregate. Money stays a :class:`~decimal.Decimal` all the way to
the edge, which is the only place it becomes a string; a float anywhere on this
path would round a figure the operator subtracts from their income.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

__all__ = ["CategoryTotal", "ExpenseLedgerView", "ExpenseView"]


@dataclass(frozen=True, slots=True)
class ExpenseView:
    """One recorded cost, as the operator reads it back."""

    id: str
    amount: Decimal
    category: str
    purpose: str
    spent_at: date
    note: str
    #: ``None`` for a platform-wide cost. The name is resolved at read time, so a
    #: renamed organization reads correctly on rows entered before the rename.
    organization_id: str | None
    organization_name: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    """What one article of spending comes to across the rows in scope."""

    category: str
    amount: Decimal
    count: int


@dataclass(frozen=True, slots=True)
class ExpenseLedgerView:
    """The expenses matching the operator's filters, with their totals.

    The totals are of *these* rows and no others: they move with the filters, which
    is what makes "how much did marketing cost this spring" a question the screen
    can answer without a second endpoint.
    """

    expenses: Sequence[ExpenseView] = field(default_factory=tuple)
    total: Decimal = Decimal("0.00")
    by_category: Sequence[CategoryTotal] = field(default_factory=tuple)
    #: Whether the list was cut short by the limit — a truncated total is a wrong
    #: total, and a screen that did not say so would be quietly lying.
    truncated: bool = False
