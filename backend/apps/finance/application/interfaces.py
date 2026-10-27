"""Application ports (contracts) required by Finance use cases.

Pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case depends only on these; concrete adapters live under ``infrastructure/`` and
are injected at composition time. **Framework-free**: standard library only.

:class:`OrganizationDirectory` is a read-only window onto another context. It
exists because a cost recorded against an organization has to be readable as
"«Взлёт талантов» — хостинг", and this context stores only the id. The name is
resolved at read time rather than copied onto the row: unlike a review, which
freezes the festival it praises, an expense is the operator's own bookkeeping and
should follow a renamed client.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from apps.finance.domain.entities import CommissionPayment, PlatformExpense
from apps.finance.domain.value_objects import ExpenseCategory

__all__ = [
    "Clock",
    "CommissionPaymentRepository",
    "ExpenseRepository",
    "OrganizationDirectory",
    "UuidGenerator",
]


@runtime_checkable
class Clock(Protocol):
    """Port: the current instant, always timezone-aware UTC."""

    def utcnow(self) -> datetime: ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: fresh time-ordered identifiers."""

    def new(self) -> uuid.UUID: ...


@runtime_checkable
class ExpenseRepository(Protocol):
    """Port: persistence & retrieval of :class:`PlatformExpense` aggregates.

    ``list_expenses`` takes its filters apart rather than as one opaque query
    object: each is a control on the operator's screen, and every one of them is
    optional in the same way — absent means "do not narrow by this".
    """

    def add(self, expense: PlatformExpense) -> None: ...

    def get(self, expense_id: uuid.UUID) -> PlatformExpense | None: ...

    def save(self, expense: PlatformExpense) -> None: ...

    def list_expenses(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        category: ExpenseCategory | None = None,
        since: date | None = None,
        until: date | None = None,
        limit: int | None = None,
    ) -> Sequence[PlatformExpense]: ...

    def soft_delete(self, expense: PlatformExpense, *, now: datetime) -> None: ...


@runtime_checkable
class CommissionPaymentRepository(Protocol):
    """Port: persistence & retrieval of :class:`CommissionPayment` aggregates.

    ``totals_by_organization`` is here rather than derived from ``list_payments``
    because the dashboard wants one figure per client and never the receipts behind
    it. Summing a year of rows in Python to throw them away is the kind of read that
    only shows up as a slow console six months later.
    """

    def add(self, payment: CommissionPayment) -> None: ...

    def get(self, payment_id: uuid.UUID) -> CommissionPayment | None: ...

    def save(self, payment: CommissionPayment) -> None: ...

    def list_payments(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        since: date | None = None,
        until: date | None = None,
        limit: int | None = None,
    ) -> Sequence[CommissionPayment]: ...

    def totals_by_organization(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> dict[uuid.UUID, Decimal]: ...

    def soft_delete(self, payment: CommissionPayment, *, now: datetime) -> None: ...


@runtime_checkable
class OrganizationDirectory(Protocol):
    """Port: what the connected organizations are called, for the ledger's rows."""

    def names(self) -> dict[uuid.UUID, str]: ...
