"""Application ports (contracts) required by Organization use cases.

The **outbound dependencies** of the Organization application layer, expressed as
pure :class:`typing.Protocol` seams (ARCH-001 §7.3, Dependency Inversion). A use
case depends only on these abstractions; concrete adapters (Django ORM
repositories, a token hasher, an email provider, a clock) live in
``infrastructure/`` and are injected at composition time. The dependency arrow
points *inward*: infrastructure depends on this module, never the reverse.

**Framework-free** (ARCH-001 §4.1, §7.2): standard library only. Interfaces only,
no implementations. Repository getters return ``... | None`` so the *use case*
decides whether absence is an error.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.organization.domain.entities import Organization, StaffInvitation, StaffMembership
from apps.organization.domain.events import DomainEvent
from apps.organization.domain.value_objects import (
    InvitationTokenHash,
    OrganizationId,
    StaffEmail,
    StaffInvitationId,
    StaffMembershipId,
    StaffUserId,
)

__all__ = [
    "Clock",
    "EmailGateway",
    "EventPublisher",
    "InvitationTokenService",
    "IssuedInvitationToken",
    "OrganizationRepository",
    "StaffInvitationRepository",
    "StaffMembershipRepository",
    "TokenHasher",
    "UuidGenerator",
]


# ---------------------------------------------------------------------------
# Repository ports
# ---------------------------------------------------------------------------


@runtime_checkable
class OrganizationRepository(Protocol):
    """Port: persistence & retrieval of the singleton :class:`Organization`."""

    def get(self, organization_id: OrganizationId) -> Organization | None:
        """Return the organization with ``organization_id``, or ``None``."""
        ...

    def get_default(self) -> Organization | None:
        """Return the singleton organization, or ``None`` if not yet seeded."""
        ...

    def save(self, organization: Organization) -> None:
        """Persist ``organization`` (insert or update), honouring its version."""
        ...


@runtime_checkable
class StaffMembershipRepository(Protocol):
    """Port: persistence & retrieval of the :class:`StaffMembership` aggregate."""

    def get(self, membership_id: StaffMembershipId) -> StaffMembership | None:
        """Return the membership with ``membership_id``, or ``None``."""
        ...

    def find_active(
        self, *, user_id: StaffUserId, organization_id: OrganizationId
    ) -> StaffMembership | None:
        """Return the user's ACTIVE membership in the organization, or ``None``.

        **The authorization query.** A non-``None`` result is the sole basis for
        granting staff access.
        """
        ...

    def exists_active(
        self, *, user_id: StaffUserId, organization_id: OrganizationId
    ) -> bool:
        """Whether the user already has an ACTIVE membership (uniqueness pre-check)."""
        ...

    def list_by_organization(
        self, organization_id: OrganizationId
    ) -> Sequence[StaffMembership]:
        """Return all non-deleted memberships of the organization."""
        ...

    def save(self, membership: StaffMembership) -> None:
        """Persist ``membership`` (insert or update), honouring its version."""
        ...


@runtime_checkable
class StaffInvitationRepository(Protocol):
    """Port: persistence & retrieval of the :class:`StaffInvitation` aggregate."""

    def get(self, invitation_id: StaffInvitationId) -> StaffInvitation | None:
        """Return the invitation with ``invitation_id``, or ``None``."""
        ...

    def get_by_token_hash(self, token_hash: InvitationTokenHash) -> StaffInvitation | None:
        """Return the invitation whose token digest is ``token_hash``, or ``None``."""
        ...

    def find_pending_by_email(
        self, *, email: StaffEmail, organization_id: OrganizationId
    ) -> StaffInvitation | None:
        """Return an open invitation for ``email`` in the organization, or ``None``."""
        ...

    def save(self, invitation: StaffInvitation) -> None:
        """Persist ``invitation`` (insert or update), honouring its version."""
        ...


# ---------------------------------------------------------------------------
# Gateway & security ports
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IssuedInvitationToken:
    """A freshly minted invitation secret paired with its digest.

    :attr:`raw_token` is the high-entropy secret that goes into the emailed link
    and is **never persisted**; :attr:`token_hash` is the SHA-256 digest stored on
    the invitation. Acceptance recomputes the digest of a presented raw token and
    compares digests.
    """

    raw_token: str
    token_hash: InvitationTokenHash


@runtime_checkable
class TokenHasher(Protocol):
    """Port: mint a raw invitation secret and hash a presented one.

    The raw secret is emailed and never stored; only its digest is persisted
    (same philosophy as password storage). :meth:`generate` returns a fresh
    high-entropy secret plus its digest; :meth:`hash` recomputes the digest of a
    presented secret at acceptance for a constant-time-comparable lookup.
    """

    def generate(self) -> IssuedInvitationToken:
        """Mint a fresh raw secret and its :class:`InvitationTokenHash`."""
        ...

    def hash(self, raw_token: str) -> InvitationTokenHash:
        """Compute the digest of a presented raw token, for hash-vs-hash lookup."""
        ...


@runtime_checkable
class EmailGateway(Protocol):
    """Port: deliver the staff-invitation email carrying the raw acceptance link."""

    def send_staff_invitation(
        self,
        *,
        email: StaffEmail,
        role: str,
        accept_url: str,
        expires_at: datetime,
    ) -> None:
        """Send an invitation to ``email`` with a link the invitee accepts through."""
        ...


@runtime_checkable
class InvitationTokenService(Protocol):
    """Port: render the full, user-facing acceptance link from a raw token."""

    def build_accept_url(self, *, raw_token: str) -> str:
        """Return the complete web-client URL that accepts ``raw_token``."""
        ...


# ---------------------------------------------------------------------------
# Ambient-dependency ports (time & identity, injected not read globally)
# ---------------------------------------------------------------------------


@runtime_checkable
class Clock(Protocol):
    """Port: the current instant, injected rather than read globally."""

    def now(self) -> datetime:
        """The current instant as a timezone-aware datetime (possibly non-UTC)."""
        ...

    def utcnow(self) -> datetime:
        """The current instant as a timezone-aware **UTC** datetime."""
        ...


@runtime_checkable
class UuidGenerator(Protocol):
    """Port: source of fresh UUID v7 identifiers, injected rather than read globally."""

    def new(self) -> uuid.UUID:
        """Return a brand-new time-ordered UUID version 7."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """Port: dispatch recorded domain events to the world outside the aggregate."""

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publish ``events`` in order to the platform's event transport."""
        ...
