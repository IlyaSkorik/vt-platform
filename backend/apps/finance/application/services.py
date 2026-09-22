"""Use cases of the Finance bounded context — the platform's own expense book.

One audience only: the platform operator. There is no organizer-facing use case
here and there should not be one — what the platform spends is not an organization's
business, and the commission it charges them is decided on the terms screen, not
in this ledger.

The service is deliberately thin. Recording a cost is entering four values and a
date; the interesting arithmetic — income minus these, per organization — lives in
the console's dashboard projection, because it needs the commission figures that
this context does not own and should not fetch.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import date
from decimal import Decimal
from typing import Final

from apps.finance.application.dto.commands import AmendExpenseCommand, RecordExpenseCommand
from apps.finance.application.dto.queries import CategoryTotal, ExpenseLedgerView, ExpenseView
from apps.finance.application.interfaces import Clock, ExpenseRepository, OrganizationDirectory, UuidGenerator
from apps.finance.domain.entities import PlatformExpense
from apps.finance.domain.exceptions import ExpenseNotFoundError, InvalidExpenseDataError
from apps.finance.domain.value_objects import ExpenseAmount, ExpenseCategory, ExpenseNote, ExpensePurpose

__all__ = ["ExpenseService"]

#: How many rows one read of the ledger returns. Generous — an operator scrolling a
#: year of bookkeeping should not meet a pager — but finite, because a console that
#: can be made to serialize an unbounded table is a console with an outage in it.
_LIST_LIMIT: Final = 1000


def _uuid(value: str, *, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidExpenseDataError(f"Некорректный {what}.") from exc


class ExpenseService:
    """Every Finance use case, over its repository and the organization directory."""

    def __init__(
        self,
        *,
        expenses: ExpenseRepository,
        clock: Clock,
        uuids: UuidGenerator,
        organizations: OrganizationDirectory,
    ) -> None:
        self._expenses = expenses
        self._clock = clock
        self._uuids = uuids
        self._organizations = organizations

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def record(self, command: RecordExpenseCommand) -> ExpenseView:
        """Enter one cost into the books."""
        now = self._clock.utcnow()
        expense = PlatformExpense.record(
            expense_id=self._uuids.new(),
            amount=ExpenseAmount.parse(command.amount),
            category=ExpenseCategory.parse(command.category),
            purpose=ExpensePurpose(command.purpose),
            spent_at=command.spent_at,
            now=now,
            organization_id=None if not command.organization_id else _uuid(command.organization_id, what="идентификатор организации"),
            note=ExpenseNote(command.note or ""),
            recorded_by=None if not command.recorded_by else _uuid(command.recorded_by, what="идентификатор администратора"),
        )
        self._expenses.add(expense)
        return self._view(expense, self._organizations.names())

    def amend(self, command: AmendExpenseCommand) -> ExpenseView:
        """Correct a recorded expense, leaving every field the caller omitted alone."""
        expense = self._expenses.get(_uuid(command.expense_id, what="идентификатор расхода"))
        if expense is None:
            raise ExpenseNotFoundError("Расход не найден.")
        expense.amend(
            now=self._clock.utcnow(),
            amount=None if command.amount is None else ExpenseAmount.parse(command.amount),
            category=None if command.category is None else ExpenseCategory.parse(command.category),
            purpose=None if command.purpose is None else ExpensePurpose(command.purpose),
            spent_at=command.spent_at,
            note=None if command.note is None else ExpenseNote(command.note),
            organization=None if not command.organization_id else _uuid(command.organization_id, what="идентификатор организации"),
            reassign=command.reassign,
        )
        self._expenses.save(expense)
        return self._view(expense, self._organizations.names())

    def remove(self, expense_id: uuid.UUID) -> None:
        """Take a cost out of the books without erasing the row it was on."""
        expense = self._expenses.get(expense_id)
        if expense is None:
            raise ExpenseNotFoundError("Расход не найден.")
        self._expenses.soft_delete(expense, now=self._clock.utcnow())

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def ledger(
        self,
        *,
        organization_id: str | None = None,
        category: str | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> ExpenseLedgerView:
        """The expenses matching these filters, newest first, with their totals."""
        rows = self._expenses.list_expenses(
            organization_id=None if not organization_id else _uuid(organization_id, what="идентификатор организации"),
            category=None if not category else ExpenseCategory.parse(category),
            since=since,
            until=until,
            # One more than the cap, so a full page can be told apart from a page
            # that happens to end exactly at it.
            limit=_LIST_LIMIT + 1,
        )
        truncated = len(rows) > _LIST_LIMIT
        kept = rows[:_LIST_LIMIT]
        names = self._organizations.names()
        return ExpenseLedgerView(
            expenses=[self._view(expense, names) for expense in kept],
            total=sum((expense.amount.value for expense in kept), Decimal("0.00")),
            by_category=_by_category(kept),
            truncated=truncated,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _view(expense: PlatformExpense, names: dict[uuid.UUID, str]) -> ExpenseView:
        organization_id = expense.organization_id
        return ExpenseView(
            id=str(expense.id),
            amount=expense.amount.value,
            category=str(expense.category),
            purpose=expense.purpose.value,
            spent_at=expense.spent_at,
            note=expense.note.value,
            organization_id=None if organization_id is None else str(organization_id),
            # An organization that has since been erased leaves its id on the row and
            # no name to show; the console renders that as an expense of the platform's
            # rather than dropping a cost that was really carried.
            organization_name=None if organization_id is None else names.get(organization_id),
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )


def _by_category(expenses: Iterable[PlatformExpense]) -> Sequence[CategoryTotal]:
    """Totals per article, largest first — the order the operator reads them in."""
    sums: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    for expense in expenses:
        key = str(expense.category)
        sums[key] = sums.get(key, Decimal("0.00")) + expense.amount.value
        counts[key] = counts.get(key, 0) + 1
    totals = [CategoryTotal(category=key, amount=amount, count=counts[key]) for key, amount in sums.items()]
    totals.sort(key=lambda row: (-row.amount, row.category))
    return totals
