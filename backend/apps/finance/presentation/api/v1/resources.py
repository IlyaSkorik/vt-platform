"""Projecting Finance DTOs onto the wire.

One place where a view's JSON shape is decided, so the ledger's rows and the row
a write answers with cannot drift apart field by field as each view is edited.

Money becomes a string here and nowhere earlier: it is a ``Decimal`` all the way
from the column, and this is the last point before JSON — where a number would
become a float and round a figure the operator subtracts from their income.
"""

from __future__ import annotations

from typing import Any

from apps.finance.application.dto.queries import ExpenseLedgerView, ExpenseView

__all__ = ["expense", "ledger"]


def expense(view: ExpenseView) -> dict[str, Any]:
    return {
        "id": view.id,
        "amount": str(view.amount),
        "category": view.category,
        "purpose": view.purpose,
        "spentAt": view.spent_at,
        "note": view.note,
        "organizationId": view.organization_id,
        "organizationName": view.organization_name,
        "createdAt": view.created_at,
        "updatedAt": view.updated_at,
    }


def ledger(view: ExpenseLedgerView) -> dict[str, Any]:
    return {
        "expenses": [expense(row) for row in view.expenses],
        "total": str(view.total),
        "byCategory": [{"category": row.category, "amount": str(row.amount), "count": row.count} for row in view.by_category],
        "truncated": view.truncated,
    }
