"""Django ORM repository adapters for the Organization bounded context.

The concrete implementations of the application repository ports (ARCH-001 §7.2,
§7.3): the only components permitted to touch the Django ORM on behalf of an
Organization aggregate. Use cases speak only aggregates and value objects; these
adapters turn those into model queries and back via the mappers, and translate
every Django exception into a :mod:`.exceptions` type so no framework error leaks.
"""

from __future__ import annotations

from .django_organization_repository import DjangoOrganizationRepository
from .django_staff_invitation_repository import DjangoStaffInvitationRepository
from .django_staff_membership_repository import DjangoStaffMembershipRepository

__all__ = [
    "DjangoOrganizationRepository",
    "DjangoStaffInvitationRepository",
    "DjangoStaffMembershipRepository",
]
