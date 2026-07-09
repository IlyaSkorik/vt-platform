"""ORM models (adapters) for the Organization bounded context.

Django models live ONLY here, never in the domain (ARCH-001 §7.2, §14), and carry
NO business logic. A package (not a single module) so models are split per
aggregate. Tables are named with the ``organization_`` context prefix. The domain
layer remains the source of truth — these classes are only a database
representation the mapper/repository reads from and writes to.
"""

from __future__ import annotations

from .base import BasePersistenceModel, uuid7
from .organization import OrganizationModel, OrganizationStatusChoices
from .staff_invitation import StaffInvitationModel
from .staff_membership import (
    MembershipStatusChoices,
    StaffMembershipModel,
    StaffRoleChoices,
)

__all__ = [
    "BasePersistenceModel",
    "MembershipStatusChoices",
    "OrganizationModel",
    "OrganizationStatusChoices",
    "StaffInvitationModel",
    "StaffMembershipModel",
    "StaffRoleChoices",
    "uuid7",
]
