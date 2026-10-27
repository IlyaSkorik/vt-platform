"""Persistence for the commission the platform actually received.

One table, mirroring the :class:`~apps.finance.domain.entities.CommissionPayment`
aggregate. Cross-context references (``organization_id``, ``recorded_by``) are
id-only ``UUIDField`` columns and never foreign keys (ARCH-001 §9.2) — the
organizations live in another context, and an operator's account in another one
still.

``amount`` is a ``DecimalField`` and nothing else. These figures are subtracted
from what an organization owes, so the column that holds them may not be a float
any more than the arithmetic over them may be.

Unlike ``finance_platform_expense``, ``organization_id`` here is ``NOT NULL``: a
receipt with no payer would reduce nobody's debt.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["CommissionPaymentModel"]


class CommissionPaymentModel(BasePersistenceModel):
    """Database row for one commission payment received (persistence only)."""

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.TextField(blank=True, default="")

    # Who paid. Required — the domain refuses a receipt without a payer.
    organization_id = models.UUIDField()

    # The day the money landed, as the bank statement says — not the moment it was
    # typed in, which is ``created_at`` beside it. A month's receipts are the ones
    # dated to that month, whenever the bookkeeping caught up.
    received_at = models.DateField()
    recorded_by = models.UUIDField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "finance_commission_payment"
        verbose_name = "commission payment"
        verbose_name_plural = "commission payments"
        ordering = ["-received_at", "-created_at"]
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            # The receipts screen: newest first, optionally narrowed to one client.
            models.Index(fields=["-received_at"]),
            # The debt projection, which sums this table by organization over a period.
            models.Index(fields=["organization_id", "-received_at"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            # The domain refuses a non-positive sum; the table refuses it too, so a
            # figure that never went through an aggregate cannot become a negative
            # receipt that silently inflates what an organization still owes.
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="finance_commission_payment_amount_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.received_at}: {self.amount}"
