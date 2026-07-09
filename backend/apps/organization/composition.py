"""Composition root for the Organization bounded context.

The one place framework-free use cases and services are wired to their concrete
infrastructure adapters (ARCH-001 §7.3, Dependency Inversion). Callers — the
management command, the (Phase 3) API views, the (Phase 2) ``/users/me``
composition edge — ask this module for a fully-assembled handler or service and
stay ignorant of *which* repository, clock, hasher, or event transport sits
behind each port. Swapping an adapter (or a fake, in tests) changes only here.

Every adapter is stateless and cheap to build, so handlers/services are assembled
per call; there is no shared mutable state.
"""

from __future__ import annotations

from apps.organization.application.handlers import ProvisionOwnerHandler
from apps.organization.application.read_models import StaffMembershipReader
from apps.organization.infrastructure.messaging import EventDispatcher
from apps.organization.infrastructure.repositories import (
    DjangoOrganizationRepository,
    DjangoStaffMembershipRepository,
)
from apps.organization.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_provision_owner_handler",
    "build_staff_membership_read_service",
]


def build_provision_owner_handler() -> ProvisionOwnerHandler:
    """Assemble the bootstrap-owner use case with its adapters."""
    return ProvisionOwnerHandler(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=EventDispatcher(),
    )


def build_staff_membership_read_service() -> StaffMembershipReader:
    """Assemble the published cross-context staff-membership read model."""
    return StaffMembershipReader(
        organizations=DjangoOrganizationRepository(),
        memberships=DjangoStaffMembershipRepository(),
    )
