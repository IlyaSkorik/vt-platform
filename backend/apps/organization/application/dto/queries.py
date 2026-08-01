from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GetOrganizationProfileQuery",
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
    """List every invitation of the caller's own organization (roster read model)."""

    requested_by: str


@dataclass(frozen=True, slots=True)
class ListStaffMembersQuery:
    """List every staff member of the caller's own organization (roster read model)."""

    requested_by: str


@dataclass(frozen=True, slots=True)
class GetOrganizationProfileQuery:
    """Read the caller's own organization profile."""

    requested_by: str
