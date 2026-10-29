"""Domain exceptions for the Finance bounded context.

Every error carries a stable ``code``, which is what the REST edge maps onto an
RFC 9457 problem type (API-000 §8). Messages are the ones a person reads, so they
are written in Russian and say what to do rather than what went wrong internally.
"""

from __future__ import annotations

from typing import ClassVar

__all__ = [
    "CommissionPaymentNotFoundError",
    "ExpenseNotFoundError",
    "FinanceError",
    "InvalidCommissionPaymentDataError",
    "InvalidExpenseDataError",
]


class FinanceError(Exception):
    """Base class for every failure this context reports."""

    code: ClassVar[str] = "finance_error"


class InvalidExpenseDataError(FinanceError, ValueError):
    """A value the domain refuses: a zero sum, a missing purpose, an unknown article."""

    code: ClassVar[str] = "invalid_expense_data"


class ExpenseNotFoundError(FinanceError):
    """No such expense — it was never recorded, or it has already been removed."""

    code: ClassVar[str] = "expense_not_found"


class InvalidCommissionPaymentDataError(FinanceError, ValueError):
    """A value the domain refuses on a commission receipt: a non-positive sum, no payer."""

    code: ClassVar[str] = "invalid_commission_payment_data"


class CommissionPaymentNotFoundError(FinanceError):
    """No such receipt — it was never recorded, or it has already been struck off."""

    code: ClassVar[str] = "commission_payment_not_found"
