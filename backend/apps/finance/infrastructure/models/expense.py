"""Persistence for the platform's own expense book.

One table, mirroring the one aggregate. Cross-context references
(``organization_id``, ``recorded_by``) are id-only ``UUIDField`` columns and never
foreign keys (ARCH-001 §9.2) — the organizations live in another context, and an
operator's account in another one still.

``amount`` is a ``DecimalField`` and nothing else. These figures are subtracted
from the commission the platform invoices, so the column that holds them may not
be a float any more than the arithmetic over them may be.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["PlatformExpenseModel"]


class PlatformExpenseModel(BasePersistenceModel):
    """Database row for one cost the platform carried (persistence only)."""

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    # The article of spending — a closed list in the domain, a plain column here:
    # a database-level enum would have to be migrated every time sales invents a
    # new kind of cost, and the domain already refuses anything off the list.
    category = models.CharField(max_length=32)
    # What the money went on, in the operator's words. Never blank: the domain
    # refuses an expense without it.
    purpose = models.CharField(max_length=200)
    note = models.TextField(blank=True, default="")

    # NULL means the platform carried this itself — hosting, an accountant, an
    # advertisement for the platform rather than for one client. Not "unassigned":
    # there is nothing to assign it to.
    organization_id = models.UUIDField(null=True, blank=True, default=None)

    # The day the money went, as the invoice says — not the moment somebody typed
    # it in, which is ``created_at`` beside it. A month's expenses are the ones
    # dated to that month, whenever the bookkeeping caught up.
    spent_at = models.DateField()
    recorded_by = models.UUIDField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "finance_platform_expense"
        verbose_name = "platform expense"
        verbose_name_plural = "platform expenses"
        ordering = ["-spent_at", "-created_at"]
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            # The ledger screen: newest first, optionally narrowed to one client.
            models.Index(fields=["-spent_at"]),
            models.Index(fields=["organization_id", "-spent_at"]),
            # The profit projection, which sums this table by organization.
            models.Index(fields=["category"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            # The domain refuses a non-positive sum; the table refuses it too, so a
            # figure that never went through an aggregate cannot become a negative
            # cost that silently adds to the platform's income.
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="finance_expense_amount_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.spent_at}: {self.purpose} — {self.amount}"
