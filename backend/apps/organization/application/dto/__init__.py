"""Result & view DTOs for the Organization application layer.

Immutable, primitive-only output shapes. They are the boundary in the *outward*
direction: handlers render domain aggregates into flat, serialization-agnostic
DTOs so no outer layer needs to import the domain to read a result.

:class:`StaffMembershipView` is special — it is the **published cross-context read
model**. The ``/users/me`` composition edge and other contexts consume it to learn
a user\'s staff status without ever touching an Organization aggregate or its
value objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.organization.domain.entities import StaffInvitation, StaffMembership
from apps.organization.domain.events import DomainEvent

__all__ = [
    "InvitationOperationResultDto",
    "InvitationView",
    "MembershipOperationResultDto",
    "StaffInvitationDetailsDto",
    "StaffMembershipView",
]


@dataclass(frozen=True, slots=True)
class StaffInvitationDetailsDto:
    """A flat read view of a :class:`StaffInvitation` for the lookup endpoint."""

    organization_name: str
    role: str
    expires_at: datetime
    invited_email: str


@dataclass(frozen=True, slots=True)
class StaffMembershipView:
    """The published read model of a user's staff membership (cross-context).

    Flat and primitive-only. This is the *entire* contract other contexts see —
    intentionally minimal (role + status + org), matching the ``/users/me``
    ``staffMembership`` shape.
    """

    role: str
    status: str
    organization_id: str

    @classmethod
    def from_membership(cls, membership: StaffMembership) -> StaffMembershipView:
        """Project a :class:`StaffMembership` into its read model."""
        return cls(
            role=membership.role.value,
            status=membership.status.value,
            organization_id=membership.organization_id.json(),
        )


@dataclass(frozen=True, slots=True)
class InvitationView:
    """A flat read view of a :class:`StaffInvitation` (never carries the token)."""

    id: str
    organization_id: str
    email: str
    role: str
    expires_at: datetime
    invited_by: str
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    @classmethod
    def from_invitation(cls, invitation: StaffInvitation) -> InvitationView:
        """Project a :class:`StaffInvitation` into a DTO (excludes the token hash)."""
        return cls(
            id=invitation.id.json(),
            organization_id=invitation.organization_id.json(),
            email=invitation.email.value,
            role=invitation.role.value,
            expires_at=invitation.expires_at,
            invited_by=invitation.invited_by.json(),
            accepted_at=invitation.accepted_at,
            revoked_at=invitation.revoked_at,
            created_at=invitation.created_at,
        )


@dataclass(frozen=True, slots=True)
class InvitationOperationResultDto:
    """The outcome of an invitation command: the invitation view plus new events."""

    invitation: InvitationView
    raw_token: str
    events: tuple[DomainEvent, ...]


@dataclass(frozen=True, slots=True)
class MembershipOperationResultDto:
    """The outcome of a membership command: the membership view plus new events."""

    membership: StaffMembershipView
    events: tuple[DomainEvent, ...]
