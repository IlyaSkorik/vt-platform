"""Mapper — the ACL between the :class:`PlatformExpense` aggregate and its row.

The only component permitted to know both the framework-free aggregate and its
Django model. It translates in both directions and does nothing else: no
validation, no workflow, no ``save()``. Timestamps are copied verbatim — the
aggregate owns those instants.
"""

from __future__ import annotations

from typing import Any

from apps.finance.domain.entities import PlatformExpense
from apps.finance.domain.value_objects import ExpenseAmount, ExpenseCategory, ExpenseNote, ExpensePurpose
from apps.finance.infrastructure.models import PlatformExpenseModel

__all__ = ["ExpenseMapper"]


class ExpenseMapper:
    """Bidirectional translator between ``PlatformExpense`` and its row."""

    @staticmethod
    def to_domain(model: PlatformExpenseModel) -> PlatformExpense:
        """Reconstruct the aggregate from its row (no re-validation, no events)."""
        return PlatformExpense.rehydrate(
            expense_id=model.id,
            amount=ExpenseAmount(model.amount),
            category=ExpenseCategory.parse(model.category),
            purpose=ExpensePurpose(model.purpose),
            spent_at=model.spent_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            note=ExpenseNote(model.note),
            recorded_by=model.recorded_by,
            version=model.version,
        )

    @staticmethod
    def to_columns(expense: PlatformExpense) -> dict[str, Any]:
        """The aggregate as the columns of its row."""
        return {
            "id": expense.id,
            "amount": expense.amount.value,
            "category": str(expense.category),
            "purpose": expense.purpose.value,
            "note": expense.note.value,
            "organization_id": expense.organization_id,
            "spent_at": expense.spent_at,
            "recorded_by": expense.recorded_by,
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
            "version": expense.version,
        }
