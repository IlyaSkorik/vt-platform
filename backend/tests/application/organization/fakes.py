"""In-memory fakes for the Organization application ports.

Framework-free, database-free test doubles that structurally satisfy the ports
in :mod:`apps.organization.application.interfaces`. Not a test module (no
``test_`` prefix), so pytest does not collect it.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.organization.application.interfaces import IssuedInvitationToken
from apps.organization.domain.entities import Organization, StaffInvitation, StaffMembership
from apps.organization.domain.events import DomainEvent
from apps.organization.domain.value_objects import (
    InvitationTokenHash,
    MembershipStatus,
    OrganizationId,
    StaffEmail,
    StaffInvitationId,
    StaffMembershipId,
    StaffUserId,
)

NOW = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW

    def utcnow(self) -> datetime:
        return NOW


class SequenceUuidGenerator:
    """Deterministic UUID v7 source for reproducible ids."""

    def new(self) -> uuid.UUID:
        from apps.organization.domain.value_objects import _generate_uuid7

        return _generate_uuid7()


class RecordingEventPublisher:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)


class FakeOrganizationRepository:
    def __init__(self) -> None:
        self._by_id: dict[OrganizationId, Organization] = {}
        self.saved: list[Organization] = []

    def get(self, organization_id: OrganizationId) -> Organization | None:
        return self._by_id.get(organization_id)

    def get_default(self) -> Organization | None:
        return next(iter(self._by_id.values()), None)

    def save(self, organization: Organization) -> None:
        self._by_id[organization.id] = organization
        self.saved.append(organization)

    def seed(self, organization: Organization) -> Organization:
        self._by_id[organization.id] = organization
        return organization


class FakeStaffMembershipRepository:
    def __init__(self) -> None:
        self._by_id: dict[StaffMembershipId, StaffMembership] = {}
        self.saved: list[StaffMembership] = []

    def get(self, membership_id: StaffMembershipId) -> StaffMembership | None:
        return self._by_id.get(membership_id)

    def find_active(
        self, *, user_id: StaffUserId, organization_id: OrganizationId
    ) -> StaffMembership | None:
        return next(
            (
                m
                for m in self._by_id.values()
                if m.user_id == user_id
                and m.organization_id == organization_id
                and m.status is MembershipStatus.ACTIVE
            ),
            None,
        )

    def exists_active(
        self, *, user_id: StaffUserId, organization_id: OrganizationId
    ) -> bool:
        return self.find_active(user_id=user_id, organization_id=organization_id) is not None

    def list_by_organization(
        self, organization_id: OrganizationId
    ) -> Sequence[StaffMembership]:
        return [m for m in self._by_id.values() if m.organization_id == organization_id]

    def save(self, membership: StaffMembership) -> None:
        self._by_id[membership.id] = membership
        self.saved.append(membership)


class FakeStaffInvitationRepository:
    def __init__(self) -> None:
        self._by_id: dict[StaffInvitationId, StaffInvitation] = {}
        self.saved: list[StaffInvitation] = []

    def get(self, invitation_id: StaffInvitationId) -> StaffInvitation | None:
        return self._by_id.get(invitation_id)

    def get_by_token_hash(self, token_hash: InvitationTokenHash) -> StaffInvitation | None:
        return next(
            (i for i in self._by_id.values() if i.token_hash == token_hash), None
        )

    def find_pending_by_email(
        self, *, email: StaffEmail, organization_id: OrganizationId
    ) -> StaffInvitation | None:
        return next(
            (
                i
                for i in self._by_id.values()
                if i.email == email
                and i.organization_id == organization_id
                and i.is_pending()
            ),
            None,
        )

    def save(self, invitation: StaffInvitation) -> None:
        self._by_id[invitation.id] = invitation
        self.saved.append(invitation)


class FakeTokenHasher:
    """Deterministic real SHA-256 hasher (no randomness beyond the secret)."""

    def generate(self) -> IssuedInvitationToken:
        raw = "raw-secret-token"
        return IssuedInvitationToken(raw_token=raw, token_hash=self.hash(raw))

    def hash(self, raw_token: str) -> InvitationTokenHash:
        return InvitationTokenHash(hashlib.sha256(raw_token.encode()).hexdigest())
