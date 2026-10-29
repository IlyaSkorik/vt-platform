"""Projecting Finance DTOs onto the wire.

One place where a view's JSON shape is decided, so the ledger's rows and the row
a write answers with cannot drift apart field by field as each view is edited.

Money becomes a string here and nowhere earlier: it is a ``Decimal`` all the way
from the column, and this is the last point before JSON — where a number would
become a float and round a figure the operator subtracts from their income.
"""

from __future__ import annotations

from typing import Any

from apps.finance.application.dto.queries import (
    CommissionPaymentLedgerView,
    CommissionPaymentView,
    ExpenseLedgerView,
    ExpenseView,
)

__all__ = ["commission_payment", "commission_payment_ledger", "expense", "ledger"]


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


def commission_payment(view: CommissionPaymentView) -> dict[str, Any]:
    return {
        "id": view.id,
        "organizationId": view.organization_id,
        "organizationName": view.organization_name,
        "amount": str(view.amount),
        "receivedAt": view.received_at,
        "note": view.note,
        "createdAt": view.created_at,
        "updatedAt": view.updated_at,
    }


def commission_payment_ledger(view: CommissionPaymentLedgerView) -> dict[str, Any]:
    return {
        "payments": [commission_payment(row) for row in view.payments],
        "total": str(view.total),
        "byOrganization": [
            {
                "organizationId": row.organization_id,
                "organizationName": row.organization_name,
                "amount": str(row.amount),
                "count": row.count,
            }
            for row in view.by_organization
        ],
        "truncated": view.truncated,
    }
