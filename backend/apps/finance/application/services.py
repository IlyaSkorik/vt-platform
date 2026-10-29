"""Use cases of the Finance bounded context — the platform's own books.

One audience only: the platform operator. There is no organizer-facing use case
here and there should not be one — what the platform spends is not an organization's
business, and the commission it charges them is decided on the terms screen, not
in this ledger.

Two services, one per side of the books: :class:`ExpenseService` for what the
platform spent, :class:`CommissionPaymentService` for what organizations paid it.
They share no state and deliberately no base class — the only thing they have in
common is the shape of a ledger read, and merging them would mean one object whose
every method applies to half its callers.

Both are deliberately thin. Recording a cost is entering four values and a date;
recording a receipt is three. The interesting arithmetic — what was accrued, less
what arrived, less what was spent, per organization — lives in the console's
dashboard projection, because it needs the commission figures that this context
does not own and should not fetch.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import date
from decimal import Decimal
from typing import Final

from apps.finance.application.dto.commands import (
    AmendCommissionPaymentCommand,
    AmendExpenseCommand,
    RecordCommissionPaymentCommand,
    RecordExpenseCommand,
)
from apps.finance.application.dto.queries import (
    CategoryTotal,
    CommissionPaymentLedgerView,
    CommissionPaymentView,
    ExpenseLedgerView,
    ExpenseView,
    OrganizationPaymentTotal,
)
from apps.finance.application.interfaces import (
    Clock,
    CommissionPaymentRepository,
    ExpenseRepository,
    OrganizationDirectory,
    UuidGenerator,
)
from apps.finance.domain.entities import CommissionPayment, PlatformExpense
from apps.finance.domain.exceptions import (
    CommissionPaymentNotFoundError,
    ExpenseNotFoundError,
    InvalidCommissionPaymentDataError,
    InvalidExpenseDataError,
)
from apps.finance.domain.value_objects import (
    ExpenseAmount,
    ExpenseCategory,
    ExpenseNote,
    ExpensePurpose,
    PaymentAmount,
    PaymentNote,
)

__all__ = ["CommissionPaymentService", "ExpenseService"]

#: How many rows one read of the ledger returns. Generous — an operator scrolling a
#: year of bookkeeping should not meet a pager — but finite, because a console that
#: can be made to serialize an unbounded table is a console with an outage in it.
_LIST_LIMIT: Final = 1000


def _uuid(value: str, *, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidExpenseDataError(f"Некорректный {what}.") from exc


def _payment_uuid(value: str, *, what: str) -> uuid.UUID:
    """The same parse, raising the receipts ledger's own error.

    Separate from :func:`_uuid` only so a malformed id on a receipts route answers
    with ``invalid_commission_payment_data`` rather than with the expense book's
    code. Both render as a 400; a client keying off ``type`` should not have to
    learn that one ledger reports the other's errors.
    """
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidCommissionPaymentDataError(f"Некорректный {what}.") from exc


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


class CommissionPaymentService:
    """Every receipts use case, over its repository and the organization directory.

    Thin for the same reason :class:`ExpenseService` is: recording a receipt is a
    payer, a sum and a date. The arithmetic that matters — what was accrued, less
    what arrived — needs the commission figures this context does not own, and so
    lives in the console's dashboard projection, which reads
    :meth:`totals_by_organization` from here and the performances from elsewhere.
    """

    def __init__(
        self,
        *,
        payments: CommissionPaymentRepository,
        clock: Clock,
        uuids: UuidGenerator,
        organizations: OrganizationDirectory,
    ) -> None:
        self._payments = payments
        self._clock = clock
        self._uuids = uuids
        self._organizations = organizations

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def record(self, command: RecordCommissionPaymentCommand) -> CommissionPaymentView:
        """Enter one receipt into the books."""
        organization_id = _payment_uuid(command.organization_id, what="идентификатор организации")
        names = self._organizations.names()
        # An organization the platform does not have on its books cannot have paid
        # it: the console only ever offers connected ones, so an id that resolves to
        # nothing is a typed-in or stale value, and accepting it would park money
        # against a client that will never appear in any total.
        if organization_id not in names:
            raise InvalidCommissionPaymentDataError("Организация не найдена.")
        payment = CommissionPayment.record(
            payment_id=self._uuids.new(),
            organization_id=organization_id,
            amount=PaymentAmount.parse(command.amount),
            received_at=command.received_at,
            now=self._clock.utcnow(),
            note=PaymentNote(command.note or ""),
            recorded_by=None if not command.recorded_by else _payment_uuid(command.recorded_by, what="идентификатор администратора"),
        )
        self._payments.add(payment)
        return self._view(payment, names)

    def amend(self, command: AmendCommissionPaymentCommand) -> CommissionPaymentView:
        """Correct a recorded receipt, leaving every field the caller omitted alone."""
        payment = self._payments.get(_payment_uuid(command.payment_id, what="идентификатор поступления"))
        if payment is None:
            raise CommissionPaymentNotFoundError("Поступление не найдено.")
        names = self._organizations.names()
        organization_id = None
        if command.organization_id:
            organization_id = _payment_uuid(command.organization_id, what="идентификатор организации")
            if organization_id not in names:
                raise InvalidCommissionPaymentDataError("Организация не найдена.")
        payment.amend(
            now=self._clock.utcnow(),
            amount=None if command.amount is None else PaymentAmount.parse(command.amount),
            received_at=command.received_at,
            note=None if command.note is None else PaymentNote(command.note),
            organization_id=organization_id,
        )
        self._payments.save(payment)
        return self._view(payment, names)

    def remove(self, payment_id: uuid.UUID) -> None:
        """Take a receipt out of the books without erasing the row it was on."""
        payment = self._payments.get(payment_id)
        if payment is None:
            raise CommissionPaymentNotFoundError("Поступление не найдено.")
        self._payments.soft_delete(payment, now=self._clock.utcnow())

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def ledger(
        self,
        *,
        organization_id: str | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> CommissionPaymentLedgerView:
        """The receipts matching these filters, newest first, with their totals."""
        rows = self._payments.list_payments(
            organization_id=None if not organization_id else _payment_uuid(organization_id, what="идентификатор организации"),
            since=since,
            until=until,
            # One more than the cap, so a full page can be told apart from a page
            # that happens to end exactly at it.
            limit=_LIST_LIMIT + 1,
        )
        truncated = len(rows) > _LIST_LIMIT
        kept = rows[:_LIST_LIMIT]
        names = self._organizations.names()
        return CommissionPaymentLedgerView(
            payments=[self._view(payment, names) for payment in kept],
            total=sum((payment.amount.value for payment in kept), Decimal("0.00")),
            by_organization=_by_organization(kept, names),
            truncated=truncated,
        )

    def totals_by_organization(
        self,
        *,
        organization_id: str | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> dict[uuid.UUID, Decimal]:
        """What each organization has paid over the period — the dashboard's input.

        Returns raw ids and sums rather than a view: the caller is a projection that
        joins this onto its own per-organization lines, and a rendered row would only
        have to be taken apart again.
        """
        return self._payments.totals_by_organization(
            organization_id=None if not organization_id else _payment_uuid(organization_id, what="идентификатор организации"),
            since=since,
            until=until,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _view(payment: CommissionPayment, names: dict[uuid.UUID, str]) -> CommissionPaymentView:
        return CommissionPaymentView(
            id=str(payment.id),
            organization_id=str(payment.organization_id),
            organization_name=names.get(payment.organization_id),
            amount=payment.amount.value,
            received_at=payment.received_at,
            note=payment.note.value,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )


def _by_organization(payments: Iterable[CommissionPayment], names: dict[uuid.UUID, str]) -> Sequence[OrganizationPaymentTotal]:
    """Totals per payer, largest first — the order the operator reads them in."""
    sums: dict[uuid.UUID, Decimal] = {}
    counts: dict[uuid.UUID, int] = {}
    for payment in payments:
        key = payment.organization_id
        sums[key] = sums.get(key, Decimal("0.00")) + payment.amount.value
        counts[key] = counts.get(key, 0) + 1
    totals = [
        OrganizationPaymentTotal(
            organization_id=str(key),
            organization_name=names.get(key),
            amount=amount,
            count=counts[key],
        )
        for key, amount in sums.items()
    ]
    totals.sort(key=lambda row: (-row.amount, row.organization_name or "", row.organization_id))
    return totals
