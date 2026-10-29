"""``DjangoCommissionPaymentRepository`` — ORM adapter for the receipts ledger.

Corrections are guarded on the version the aggregate was read at, for the same
reason the expense book guards them: two operators fixing the same figure from two
tabs must not end with one of the fixes silently lost, because the number that
survives is the one an organization's debt is computed from.

Removal is a soft delete. A receipt struck from the books is still a receipt that
was once in them, and last month's debt total has to stay explainable.

``totals_by_organization`` sums in the database rather than row by row: the
dashboard needs one figure per organization and never the rows behind it, and
loading a year of receipts to add them up in Python would make the console's
slowest query the one nobody reads.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

from django.db import DatabaseError, IntegrityError, models, transaction

from apps.finance.domain.entities import CommissionPayment
from apps.finance.infrastructure.mappers import CommissionPaymentMapper
from apps.finance.infrastructure.models import CommissionPaymentModel

from .exceptions import ConcurrencyConflictError, IntegrityViolationError, PersistenceError

__all__ = ["DjangoCommissionPaymentRepository"]


class DjangoCommissionPaymentRepository:
    """Django ORM adapter implementing the ``CommissionPaymentRepository`` port."""

    def add(self, payment: CommissionPayment) -> None:
        """Insert one receipt."""
        try:
            CommissionPaymentModel.objects.create(**CommissionPaymentMapper.to_columns(payment))
            payment.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to store the commission payment {payment.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to store the commission payment {payment.id}.") from exc

    def get(self, payment_id: uuid.UUID) -> CommissionPayment | None:
        """One receipt, or ``None`` if it is gone."""
        try:
            model = CommissionPaymentModel.objects.filter(pk=payment_id, deleted_at__isnull=True).first()
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to load the commission payment {payment_id}.") from exc
        return CommissionPaymentMapper.to_domain(model) if model is not None else None

    def save(self, payment: CommissionPayment) -> None:
        """Write a correction back, guarded on the version it was read at."""
        columns = CommissionPaymentMapper.to_columns(payment)
        expected = payment.persisted_version
        try:
            with transaction.atomic():
                if expected is None:
                    CommissionPaymentModel.objects.create(**columns)
                else:
                    updated = CommissionPaymentModel.objects.filter(pk=payment.id, version=expected).update(
                        **{name: value for name, value in columns.items() if name != "id"}
                    )
                    if not updated:
                        raise ConcurrencyConflictError(f"Commission payment {payment.id} was modified concurrently; expected version {expected}.")
                payment.mark_persisted()
        except IntegrityError as exc:
            raise IntegrityViolationError(f"Failed to persist the commission payment {payment.id}.") from exc
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to persist the commission payment {payment.id}.") from exc

    def list_payments(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        since: date | None = None,
        until: date | None = None,
        limit: int | None = None,
    ) -> Sequence[CommissionPayment]:
        """The receipts matching these filters, newest first.

        ``since``/``until`` are both inclusive and read against ``received_at``, not
        against when the row was typed: "март" means the money that landed in March,
        whenever the bookkeeping caught up with it.
        """
        try:
            query = CommissionPaymentModel.objects.filter(deleted_at__isnull=True)
            if organization_id is not None:
                query = query.filter(organization_id=organization_id)
            if since is not None:
                query = query.filter(received_at__gte=since)
            if until is not None:
                query = query.filter(received_at__lte=until)
            query = query.order_by("-received_at", "-created_at")
            rows = list(query[:limit] if limit else query)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to list commission payments.") from exc
        return [CommissionPaymentMapper.to_domain(model) for model in rows]

    def totals_by_organization(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> dict[uuid.UUID, Decimal]:
        """What each organization has paid over the period, summed in the database.

        Organizations that paid nothing are absent rather than zero: the caller is
        iterating its own list of organizations and reads a missing key as nothing
        received, which is the same answer without a row per silent client.
        """
        try:
            query = CommissionPaymentModel.objects.filter(deleted_at__isnull=True)
            if organization_id is not None:
                query = query.filter(organization_id=organization_id)
            if since is not None:
                query = query.filter(received_at__gte=since)
            if until is not None:
                query = query.filter(received_at__lte=until)
            rows = query.values("organization_id").annotate(total=models.Sum("amount"))
            return {row["organization_id"]: Decimal(str(row["total"] or "0.00")) for row in rows}
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError("Failed to total commission payments.") from exc

    def soft_delete(self, payment: CommissionPayment, *, now: datetime) -> None:
        """Take the receipt out of every total without erasing the row."""
        try:
            CommissionPaymentModel.objects.filter(pk=payment.id).update(deleted_at=now, updated_at=now)
        except DatabaseError as exc:  # pragma: no cover - defensive
            raise PersistenceError(f"Failed to delete the commission payment {payment.id}.") from exc
