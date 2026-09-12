"""The published cross-context read models of the Organization context.

Three seams other bounded contexts (and the ``/users/me`` composition edge) read
this context through: whether a user is staff
(:class:`StaffMembershipReadService`), who an organizer publicly is
(:class:`OrganizationDirectory`), and which modules an organization holds
(:class:`EnabledModulesReadService`).

Consumers depend on these ports and receive flat, primitive-only views — they
never import an Organization aggregate, repository, or value object, so no
business logic leaks across the boundary (ARCH-001 §14).

The ports live in the application layer (framework-free); their concrete
implementations are assembled at the composition root over the repositories.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from apps.organization.application.dto import StaffMembershipView
from apps.organization.application.interfaces import (
    ModuleEntitlementRepository,
    OrganizationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.value_objects import OrganizationId, StaffUserId

__all__ = [
    "EnabledModulesReadService",
    "EnabledModulesReader",
    "ModuleCache",
    "OrganizationDirectory",
    "OrganizerCardView",
    "StaffMembershipReadService",
    "StaffMembershipReader",
    "SupportingOrganizationCardView",
]


@dataclass(frozen=True, slots=True)
class SupportingOrganizationCardView:
    """Published read model of the entity a festival runs *with the support of*.

    The organizer of record and the legal person actually doing the work are often
    two different entities, and naming the second one is a legal requirement rather
    than a courtesy. Mirrors
    :class:`~apps.organization.domain.value_objects.SupportingOrganization` — the
    same channels as the organizer's own card, plus its own ``name``, since it is a
    different legal person. Absent as a whole (``None`` on the card) when the
    organization has named no supporting entity, which is the ordinary case.
    """

    name: str
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    vk: str | None = None
    instagram: str | None = None
    telegram: str | None = None
    legal_information: str | None = None


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
    #: The supporting entity beside this organizer, when it has named one.
    supporter: SupportingOrganizationCardView | None = None


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
class EnabledModulesReadService(Protocol):
    """Port: answer "which modules does this organization hold?" for other contexts.

    The **only** seam through which a module gate is decided. Consumers receive a
    set of plain module names and never import an entitlement, a repository or the
    Organization aggregate — so the question "may this organization do X" has one
    answer everywhere and cannot drift between the permission class, the navigation
    and ``/users/me``.
    """

    def for_organization(self, organization_id: uuid.UUID) -> frozenset[str]:
        """Return the module names the organization currently holds."""
        ...

    def is_enabled(self, *, organization_id: uuid.UUID, module: str) -> bool:
        """Whether the organization holds ``module`` right now."""
        ...


@runtime_checkable
class ModuleCache(Protocol):
    """Port: the memo in front of the entitlement table.

    Framework-free so the reader can be unit-tested without a cache backend, and so
    the concrete Redis/locmem adapter stays in infrastructure where it belongs.
    """

    def get(self, organization_id: uuid.UUID) -> frozenset[str] | None:
        """Return the memoized module set, or ``None`` on a miss."""
        ...

    def set(self, organization_id: uuid.UUID, modules: frozenset[str], ttl_seconds: int) -> None:
        """Memoize the module set for ``ttl_seconds``."""
        ...

    def invalidate(self, organization_id: uuid.UUID) -> None:
        """Forget the memoized set (called when an entitlement is written)."""
        ...


class EnabledModulesReader:
    """Concrete :class:`EnabledModulesReadService` over the entitlement repository.

    Cached, because this is consulted on essentially every staff request and the
    answer changes only when a platform operator moves a switch. The cache is keyed
    per organization and invalidated by the use case that writes an entitlement, so
    a revoked module stops working at once rather than at the end of a TTL — the TTL
    is only the backstop for a process that never saw the invalidation.

    An unknown module name resolves to "not held" rather than raising: a gate is a
    place to be refused, not a place to crash, and a typo in a permission class must
    close the door rather than open it.
    """

    #: Backstop only — the writer invalidates explicitly.
    CACHE_TTL_SECONDS = 300

    def __init__(self, *, entitlements: ModuleEntitlementRepository, cache: ModuleCache | None = None) -> None:
        self._entitlements = entitlements
        self._cache = cache

    def for_organization(self, organization_id: uuid.UUID) -> frozenset[str]:
        if self._cache is not None:
            cached = self._cache.get(organization_id)
            if cached is not None:
                return cached
        modules = frozenset(module.value for module in self._entitlements.enabled_modules(OrganizationId.from_uuid(organization_id)))
        if self._cache is not None:
            self._cache.set(organization_id, modules, self.CACHE_TTL_SECONDS)
        return modules

    def is_enabled(self, *, organization_id: uuid.UUID, module: str) -> bool:
        return module in self.for_organization(organization_id)


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
    design). Looks up the caller's active membership in whichever organization
    holds it: with several connected to the platform, staff status is a fact about
    a person *and* an organization, and the view carries both.
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

        "Not staff" is the normal answer here (``None``) rather than an error:
        this is consulted on every ``/users/me`` call.
        """
        membership = self._memberships.find_active_for_user(StaffUserId.from_uuid(user_id))
        if membership is None:
            return None
        return StaffMembershipView.from_membership(membership)
