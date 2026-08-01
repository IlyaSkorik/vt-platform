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
from apps.organization.domain.policies import InvitationExpiryPolicy
from apps.organization.domain.value_objects import (
    InvitationTokenHash,
    MembershipStatus,
    OrganizationId,
    OrganizationName,  # Added
    StaffEmail,
    StaffInvitationId,
    StaffMembershipId,
    StaffRole,  # Added
    StaffUserId,
)

NOW = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)


def a_staff_invitation(
    invitation_id: StaffInvitationId | None = None,
    organization_id: OrganizationId | None = None,
    email: StaffEmail | None = None,
    role: StaffRole | None = None,
    token_hash: InvitationTokenHash | None = None,
    raw_token: str | None = None,
    invited_by: StaffUserId | None = None,
    expires_at: datetime | None = None,
    now: datetime | None = None,
) -> StaffInvitation:
    _now = now if now is not None else NOW
    _invitation_id = invitation_id if invitation_id is not None else StaffInvitationId.generate()
    _organization_id = organization_id if organization_id is not None else OrganizationId.generate()
    _email = email if email is not None else StaffEmail("test@example.com")
    _role = role if role is not None else StaffRole.SUPPORT
    _raw_token = raw_token if raw_token is not None else "raw-token"
    _token_hash = token_hash if token_hash is not None else InvitationTokenHash(hashlib.sha256(_raw_token.encode()).hexdigest())
    _invited_by = invited_by if invited_by is not None else StaffUserId.from_uuid(SequenceUuidGenerator().new())
    _expires_at = expires_at if expires_at is not None else _now.replace(year=_now.year + 1)

    invitation, _ = StaffInvitation.issue(
        invitation_id=_invitation_id,
        organization_id=_organization_id,
        email=_email,
        role=_role,
        token_hash=_token_hash,
        raw_token=_raw_token,
        invited_by=_invited_by,
        policy=InvitationExpiryPolicy(),
        now=_now,
    )
    # Manually set expires_at if it was explicitly provided to the helper
    if expires_at is not None:
        invitation._expires_at = expires_at  # Directly access private attribute for test setup

    return invitation


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

    def find_by_slug(self, slug: str) -> Organization | None:
        return next((org for org in self._by_id.values() if org.slug.value == slug), None)

    def list_all(self) -> list[Organization]:
        return list(self._by_id.values())

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

    def find_active(self, *, user_id: StaffUserId, organization_id: OrganizationId) -> StaffMembership | None:
        return next(
            (
                m
                for m in self._by_id.values()
                if m.user_id == user_id and m.organization_id == organization_id and m.status is MembershipStatus.ACTIVE
            ),
            None,
        )

    def find_active_for_user(self, user_id: StaffUserId) -> StaffMembership | None:
        return next(
            (m for m in self._by_id.values() if m.user_id == user_id and m.status is MembershipStatus.ACTIVE),
            None,
        )

    def exists_active(self, *, user_id: StaffUserId, organization_id: OrganizationId) -> bool:
        return self.find_active(user_id=user_id, organization_id=organization_id) is not None

    def list_by_organization(self, organization_id: OrganizationId) -> Sequence[StaffMembership]:
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
        return next((i for i in self._by_id.values() if i.token_hash == token_hash), None)

    def find_pending_by_email(self, *, email: StaffEmail, organization_id: OrganizationId) -> StaffInvitation | None:
        return next(
            (i for i in self._by_id.values() if i.email == email and i.organization_id == organization_id and i.is_pending()),
            None,
        )

    def list_by_organization(self, organization_id: OrganizationId) -> Sequence[StaffInvitation]:
        return [i for i in self._by_id.values() if i.organization_id == organization_id]

    def save(self, invitation: StaffInvitation) -> None:
        self._by_id[invitation.id] = invitation
        self.saved.append(invitation)


class RecordingEmailGateway:
    def __init__(self) -> None:
        self.sent: list[tuple[StaffEmail, OrganizationName, StaffRole, datetime, str]] = []

    def send_staff_invitation(
        self, *, recipient_email: StaffEmail, organization_name: OrganizationName, role: StaffRole, expires_at: datetime, token: str
    ) -> None:
        self.sent.append((recipient_email, organization_name, role, expires_at, token))


class FakeUserDirectory:
    """In-memory :class:`UserDirectory` mapping user uuids to their card view."""

    def __init__(self) -> None:
        from apps.identity.application.read_models import UserCardView

        self._card_cls = UserCardView
        self._by_id: dict[uuid.UUID, object] = {}

    def add(
        self,
        user_id: uuid.UUID,
        *,
        email: str = "member@example.com",
        display_name: str = "Иван Иванов",
        status: str = "active",
    ) -> None:
        self._by_id[user_id] = self._card_cls(id=str(user_id), email=email, display_name=display_name, status=status)

    def resolve(self, user_ids: object) -> dict[uuid.UUID, object]:
        ids = {uid for uid in user_ids if uid is not None}
        return {uid: card for uid, card in self._by_id.items() if uid in ids}


class FakeTokenHasher:
    """Deterministic real SHA-256 hasher (no randomness beyond the secret)."""

    def generate(self) -> IssuedInvitationToken:
        raw = "raw-secret-token"
        return IssuedInvitationToken(raw_token=raw, token_hash=self.hash(raw))

    def hash(self, raw_token: str) -> InvitationTokenHash:
        return InvitationTokenHash(hashlib.sha256(raw_token.encode()).hexdigest())
