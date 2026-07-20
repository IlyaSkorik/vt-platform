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
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from apps.organization.application.dto import StaffMembershipView
from apps.organization.application.interfaces import (
    OrganizationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.value_objects import StaffUserId

__all__ = [
    "OrganizationDirectory",
    "OrganizerCardView",
    "StaffMembershipReadService",
    "StaffMembershipReader",
]


@dataclass(frozen=True, slots=True)
class OrganizerCardView:
    """Published read model of an organizer's public identity.

    The *entire* contract other contexts see when they need to render "who runs
    this competition" — flat and primitive-only. ``logo`` resolves to the
    organization's stored logo reference (``None`` until one is uploaded);
    consumers render an initials fallback when it is absent.

    The contact channels (phone/email/website/address/social) mirror the
    :class:`~apps.organization.domain.value_objects.OrganizationProfile` and are
    the organization's role as the "single source of truth" for competitions that
    defer to it (``use_organization_contacts``). Every channel is optional — an
    organization that has not filled in its profile resolves them all to ``None``.
    """

    id: str
    name: str
    logo: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    vk: str | None = None
    instagram: str | None = None
    telegram: str | None = None
    legal_information: str | None = None


@runtime_checkable
class OrganizationDirectory(Protocol):
    """Port: resolve organizer ids to their public :class:`OrganizerCardView`.

    A batch lookup so a read model rendering many competitions resolves every
    organizer in one call. Ids with no matching organization are simply absent
    from the returned mapping — the caller decides on a fallback rather than the
    directory inventing one.
    """

    def resolve(self, organizer_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, OrganizerCardView]:
        """Return a mapping of the given ids to their organizer card view."""
        ...

    def default_organizer(self) -> OrganizerCardView | None:
        """Return the singleton organization's card, or ``None`` if unseeded.

        The platform runs a single active organization, and a competition's
        ``organizer_id`` is not guaranteed to point at it (it is a free-form
        client-supplied grouping id). Consumers use this as the fallback identity
        and contact source when :meth:`resolve` finds no matching row, so the
        organization stays the single source of truth for the public page.
        """
        ...


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
        membership = self._memberships.find_active(user_id=staff_user_id, organization_id=organization.id)
        if membership is None:
            return None
        return StaffMembershipView.from_membership(membership)
