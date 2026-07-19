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
    "UpdateOrganizationProfileCommand",
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
    ``email`` is the authenticated user's email address, used to verify the
    invitation belongs to the person accepting it.
    """

    raw_token: str
    accepted_by: str
    email: str


@dataclass(frozen=True, slots=True)
class RevokeStaffMembershipCommand:
    """Revoke an active staff membership."""

    membership_id: str
    revoked_by: str


@dataclass(frozen=True, slots=True)
class UpdateOrganizationProfileCommand:
    """Replace the organization's public contact & legal profile.

    A full-replacement edit: every field the profile form carries. An omitted /
    cleared contact field arrives as ``None`` and clears the stored value.
    ``name`` is the organization's display name — ``None`` means "leave unchanged"
    (the slug is never editable here). ``updated_by`` is the raw UUID of the
    authenticated staff member making the change.
    """

    updated_by: str
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    logo: str | None = None
    vk: str | None = None
    instagram: str | None = None
    telegram: str | None = None
    legal_information: str | None = None
