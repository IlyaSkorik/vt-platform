"""Composition root for the Finance bounded context.

The one place a framework-free use case is wired to its concrete adapters
(ARCH-001 §7.3, Dependency Inversion): the presentation edge asks here for an
assembled service and stays ignorant of which repository, clock or directory sits
behind each port. Adapters are stateless and cheap, so they are assembled per call.
"""

from __future__ import annotations

from apps.finance.application.services import CommissionPaymentService, ExpenseService
from apps.finance.infrastructure.acl import DjangoOrganizationDirectory
from apps.finance.infrastructure.repositories import DjangoCommissionPaymentRepository, DjangoPlatformExpenseRepository
from apps.finance.infrastructure.system import SystemClock, Uuid7Generator

__all__ = ["build_commission_payment_service", "build_expense_service"]


def build_expense_service() -> ExpenseService:
    """Assemble the Finance use cases over PostgreSQL and the real clock."""
    return ExpenseService(
        expenses=DjangoPlatformExpenseRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        organizations=DjangoOrganizationDirectory(),
    )


def build_commission_payment_service() -> CommissionPaymentService:
    """Assemble the receipts use cases over PostgreSQL and the real clock."""
    return CommissionPaymentService(
        payments=DjangoCommissionPaymentRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        organizations=DjangoOrganizationDirectory(),
    )
