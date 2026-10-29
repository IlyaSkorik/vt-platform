"""Mapper — the ACL between the :class:`CommissionPayment` aggregate and its row.

The only component permitted to know both the framework-free aggregate and its
Django model. It translates in both directions and does nothing else: no
validation, no workflow, no ``save()``. Timestamps are copied verbatim — the
aggregate owns those instants.
"""

from __future__ import annotations

from typing import Any

from apps.finance.domain.entities import CommissionPayment
from apps.finance.domain.value_objects import PaymentAmount, PaymentNote
from apps.finance.infrastructure.models import CommissionPaymentModel

__all__ = ["CommissionPaymentMapper"]


class CommissionPaymentMapper:
    """Bidirectional translator between ``CommissionPayment`` and its row."""

    @staticmethod
    def to_domain(model: CommissionPaymentModel) -> CommissionPayment:
        """Reconstruct the aggregate from its row (no re-validation, no events)."""
        return CommissionPayment.rehydrate(
            payment_id=model.id,
            organization_id=model.organization_id,
            amount=PaymentAmount(model.amount),
            received_at=model.received_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            note=PaymentNote(model.note),
            recorded_by=model.recorded_by,
            version=model.version,
        )

    @staticmethod
    def to_columns(payment: CommissionPayment) -> dict[str, Any]:
        """The aggregate as the columns of its row."""
        return {
            "id": payment.id,
            "amount": payment.amount.value,
            "note": payment.note.value,
            "organization_id": payment.organization_id,
            "received_at": payment.received_at,
            "recorded_by": payment.recorded_by,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
            "version": payment.version,
        }
