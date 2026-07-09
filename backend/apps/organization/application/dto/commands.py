"""Command DTOs for the Organization bounded context.

Input shapes for state-changing use cases. Framework-neutral, frozen, slotted
dataclasses carrying only primitives — no domain value objects (handlers build
those, translating validation errors) and no framework types.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AcceptStaffInvitationCommand",
    "InviteStaffCommand",
    "ProvisionOwnerCommand",
    "RevokeStaffMembershipCommand",
]


@dataclass(frozen=True, slots=True)
class ProvisionOwnerCommand:
    """Provision the first OWNER for an existing user (bootstrap, internal only).

    ``user_id`` is the raw Identity user UUID string; the user must already exist
    (verified upstream by the management command). No invitation precedes this.
    """

    user_id: str


@dataclass(frozen=True, slots=True)
class InviteStaffCommand:
    """Invite a person (by email) to join staff with a role."""

    email: str
    role: str
    invited_by: str


@dataclass(frozen=True, slots=True)
class AcceptStaffInvitationCommand:
    """Accept a staff invitation using the raw token from the emailed link.

    ``accepted_by`` is the raw UUID of the authenticated user accepting it — the
    membership binds to *this* user, not to whatever address was invited.
    """

    raw_token: str
    accepted_by: str


@dataclass(frozen=True, slots=True)
class RevokeStaffMembershipCommand:
    """Revoke an active staff membership."""

    membership_id: str
    revoked_by: str
