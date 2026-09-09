"""Resolving *which* organization a staff use case is acting inside.

The platform hosts many organizations, so no staff use case may reach for "the"
organization any more: it acts inside the caller's own, and the caller's active
membership is what names it. Everything staff-facing goes through here, which is
what keeps one organization's staff from reading or editing another's.

An actor with no active membership is refused rather than silently defaulted —
"not staff anywhere" must never resolve to "staff of the first organization".
"""

from __future__ import annotations

from apps.organization.application.exceptions import (
    OrganizationNotFoundError,
    PermissionDeniedError,
)
from apps.organization.application.interfaces import (
    OrganizationRepository,
    StaffMembershipRepository,
)
from apps.organization.domain.entities import Organization, StaffMembership
from apps.organization.domain.value_objects import StaffUserId

__all__ = ["actor_membership", "organization_of_actor"]


def actor_membership(
    actor: StaffUserId,
    *,
    memberships: StaffMembershipRepository,
) -> StaffMembership:
    """The actor's active staff membership, or refuse the action."""
    membership = memberships.find_active_for_user(actor)
    if membership is None:
        raise PermissionDeniedError("Это действие доступно только действующим сотрудникам организации.")
    return membership


def organization_of_actor(
    actor: StaffUserId,
    *,
    organizations: OrganizationRepository,
    memberships: StaffMembershipRepository,
) -> tuple[Organization, StaffMembership]:
    """The organization the actor is staff of, together with their membership."""
    membership = actor_membership(actor, memberships=memberships)
    organization = organizations.get(membership.organization_id)
    if organization is None:
        raise OrganizationNotFoundError("Организация больше не существует.")
    return organization, membership
