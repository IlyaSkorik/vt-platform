"""``DjangoPlatformExpenseRepository`` — ORM adapter for the expense book.

Corrections are guarded on the version the aggregate was read at: two operators
fixing the same figure from two tabs must not end with one of the fixes silently
lost, because the number that survives is the one a profit total is computed from.

Removal is a soft delete. A cost struck from the books is still a cost that was
once in them, and last month's total has to stay explainable.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime

from django.db import DatabaseError, IntegrityError, transaction

from apps.finance.domain.entities import PlatformExpense
from apps.finance.domain.value_objects import ExpenseCategory
from apps.finance.infrastructure.mappers import ExpenseMapper
from apps.finance.infrastructure.models import PlatformExpenseModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoPlatformExpenseRepository"]


class DjangoPlatformExpenseRepository:
    """Django ORM adapter implementing the ``ExpenseRepository`` port."""

    def add(self, expense: PlatformExpense) -> None:
        """Insert one expense."""
        try:
            PlatformExpenseModel.objects.create(**ExpenseMapper.to_columns(expense))
            expense.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to store the expense {expense.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to store the expense {expense.id}.") from exc

    def get(self, expense_id: uuid.UUID) -> PlatformExpense | None:
        """One expense, or ``None`` if it is gone."""
        try:
            model = PlatformExpenseModel.objects.filter(pk=expense_id, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load the expense {expense_id}.") from exc
        return ExpenseMapper.to_domain(model) if model is not None else None

    def save(self, expense: PlatformExpense) -> None:
        """Write a correction back, guarded on the version it was read at."""
        columns = ExpenseMapper.to_columns(expense)
        expected = expense.persisted_version
        try:
            with transaction.atomic():
                if expected is None:
                    PlatformExpenseModel.objects.create(**columns)
                else:
                    updated = PlatformExpenseModel.objects.filter(pk=expense.id, version=expected).update(
                        **{name: value for name, value in columns.items() if name != "id"}
                    )
                    if not updated:
                        raise ConcurrencyConflictError(f"Expense {expense.id} was modified concurrently; expected version {expected}.")
                expense.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist the expense {expense.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist the expense {expense.id}.") from exc

    def list_expenses(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        category: ExpenseCategory | None = None,
        since: date | None = None,
        until: date | None = None,
        limit: int | None = None,
    ) -> Sequence[PlatformExpense]:
        """The expenses matching these filters, newest first.

        ``since``/``until`` are both inclusive and read against ``spent_at``, not
        against when the row was typed: "март" means the costs dated to March,
        whenever the bookkeeping caught up with them.
        """
        try:
            query = PlatformExpenseModel.objects.filter(deleted_at__isnull=True)
            if organization_id is not None:
                query = query.filter(organization_id=organization_id)
            if category is not None:
                query = query.filter(category=str(category))
            if since is not None:
                query = query.filter(spent_at__gte=since)
            if until is not None:
                query = query.filter(spent_at__lte=until)
            query = query.order_by("-spent_at", "-created_at")
            models = list(query[:limit] if limit else query)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list expenses.") from exc
        return [ExpenseMapper.to_domain(model) for model in models]

    def soft_delete(self, expense: PlatformExpense, *, now: datetime) -> None:
        """Take the expense out of every total without erasing the row."""
        try:
            PlatformExpenseModel.objects.filter(pk=expense.id).update(deleted_at=now, updated_at=now)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to delete the expense {expense.id}.") from exc
