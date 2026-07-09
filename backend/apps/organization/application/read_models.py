"""The published cross-context read model of Organization staff status.

:class:`StaffMembershipReadService` is the **only** seam other bounded contexts
(and the ``/users/me`` composition edge) use to learn whether a user is staff.
Consumers depend on this port and receive a flat :class:`StaffMembershipView` —
they never import an Organization aggregate, repository, or value object, so no
business logic leaks across the boundary (ARCH-001 §14).

The port lives in the application layer (framework-free); its concrete
implementation is assembled at the composition root over the repositories.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from apps.organization.application.dto import StaffMembershipView
from apps.organization.application.interfaces import (
    OrganizationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.value_objects import StaffUserId

__all__ = ["StaffMembershipReadService", "StaffMembershipReader"]


@runtime_checkable
class StaffMembershipReadService(Protocol):
    """Port: answer "is this user active staff, and as what?" for other contexts.

    ``user_id`` is the raw Identity user UUID (contexts communicate by id, not by
    typed value object). Returns ``None`` when the user has no active membership —
    the common case for the vast majority of platform users.
    """

    def active_for_user(self, user_id: uuid.UUID) -> StaffMembershipView | None:
        """Return the user's active staff membership view, or ``None``."""
        ...


class StaffMembershipReader:
    """Concrete :class:`StaffMembershipReadService` over the Organization repositories.

    Structurally satisfies the port (no inheritance — the seam is structural by
    design). Resolves the singleton organization, then looks up the caller's
    active membership within it.
    """

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: StaffMembershipRepository,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships

    def active_for_user(self, user_id: uuid.UUID) -> StaffMembershipView | None:
        """Return the user's active staff membership view, or ``None``.

        A malformed id or an un-seeded organization both mean "not staff" here
        (``None``) rather than an error: this is a read model consulted on every
        ``/users/me`` call, and absence of staff is the normal answer.
        """
        organization = self._organizations.get_default()
        if organization is None:
            return None
        staff_user_id = StaffUserId.from_uuid(user_id)
        membership = self._memberships.find_active(
            user_id=staff_user_id, organization_id=organization.id
        )
        if membership is None:
            return None
        return StaffMembershipView.from_membership(membership)
