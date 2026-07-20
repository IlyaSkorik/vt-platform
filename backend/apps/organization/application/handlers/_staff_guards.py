"""Shared application-level guards for staff-membership mutations."""

from __future__ import annotations

from collections.abc import Iterable

from apps.organization.domain.entities import StaffMembership
from apps.organization.domain.value_objects import StaffRole

__all__ = ["is_sole_active_owner"]


def is_sole_active_owner(memberships: Iterable[StaffMembership], target: StaffMembership) -> bool:
    """Whether ``target`` is the organization's only remaining ACTIVE owner.

    Used by the revoke and role-change use cases to refuse any action that would
    strip the last active OWNER (which would lock the organization out of staff
    administration). Returns ``False`` unless ``target`` is itself an active owner.
    """
    if not target.has_role(StaffRole.OWNER):
        return False
    active_owners = [m for m in memberships if m.has_role(StaffRole.OWNER)]
    return len(active_owners) <= 1
