from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GetStaffInvitationQuery",
    "ListStaffInvitationsQuery",
    "ListStaffMembersQuery",
]


@dataclass(frozen=True, slots=True)
class GetStaffInvitationQuery:
    """Look up a staff invitation by the raw token from the emailed link."""

    raw_token: str


@dataclass(frozen=True, slots=True)
class ListStaffInvitationsQuery:
    """List every invitation of the singleton organization (roster read model)."""


@dataclass(frozen=True, slots=True)
class ListStaffMembersQuery:
    """List every staff member of the singleton organization (roster read model)."""
