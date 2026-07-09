"""Domain entities (aggregate roots) for the Organization bounded context.

Three aggregate roots, each its own consistency boundary and its own persistence
table. They reference one another and the Identity user **by id only** (a
value object wrapping a UUID) — never by object reference or foreign key —
keeping each aggregate independently loadable and the contexts decoupled.

* :class:`Organization`    — the singleton operating organization ("Взлёт талантов").
* :class:`StaffMembership` — the authorization fact: a user's role over the org.
* :class:`StaffInvitation` — a pending, email-based grant awaiting acceptance.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no Django,
no ORM, no clock, no IO. Time is always supplied by the caller (``now``).

Design contract (identical in spirit to the Identity ``User`` aggregate):

* **No direct construction.** Build only via a factory (``seed`` / ``issue`` /
  ``activate_for_owner`` / ``pending``) or ``rehydrate`` (reconstruction from
  persistence, which re-validates nothing and emits nothing).
* **Encapsulated state.** All fields private; only read-only properties exposed.
* **Behaviour returns events, never publishes them.** Each method validates
  invariants, mutates state, bumps ``updated_at``/``version``, and returns the
  domain events it produced. Dispatch is an outer-layer concern.
* **Invalid transitions raise** typed state errors — never silently ignored.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from datetime import datetime
from typing import Final

from .events import (
    DomainEvent,
    OrganizationReactivated,
    OrganizationSeeded,
    OrganizationSuspended,
    StaffInvitationAccepted,
    StaffInvitationIssued,
    StaffInvitationRevoked,
    StaffMembershipActivated,
    StaffMembershipRevoked,
    StaffMembershipRoleChanged,
)
from .exceptions import (
    DirectConstructionError,
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationRevokedError,
    MembershipAlreadyActiveError,
    MembershipAlreadyRevokedError,
    MembershipNotPendingError,
    OrganizationNotSuspendedError,
    OrganizationSuspendedError,
)
from .policies import InvitationExpiryPolicy
from .value_objects import (
    InvitationTokenHash,
    MembershipStatus,
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
    OrganizationStatus,
    StaffEmail,
    StaffInvitationId,
    StaffMembershipId,
    StaffRole,
    StaffUserId,
)

__all__ = ["Organization", "StaffInvitation", "StaffMembership"]

#: Opaque capability token proving construction went through a factory. Held only
#: by this module, so factories can pass it and nobody else can.
_CREATION_TOKEN: Final = object()


@dataclass(slots=True, eq=False, repr=False)
class Organization:
    """The singleton operating organization aggregate root.

    There is exactly one instance ("Взлёт талантов"), seeded via :meth:`seed`
    (used only by the data migration) and never created through a public API.
    Guards its own status transitions. Equality/hashing is by :class:`OrganizationId`.
    """

    _token: InitVar[object]
    _id: OrganizationId
    _name: OrganizationName
    _slug: OrganizationSlug
    _status: OrganizationStatus
    _created_at: datetime
    _updated_at: datetime
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError(
                "Organization must be created via Organization.seed() or "
                "Organization.rehydrate(), not by calling the constructor directly."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def seed(
        cls,
        *,
        organization_id: OrganizationId,
        name: OrganizationName,
        slug: OrganizationSlug,
        now: datetime,
    ) -> tuple[Organization, list[DomainEvent]]:
        """Create the singleton organization in the ACTIVE state.

        The only construction path for a brand-new organization; used by the seed
        data migration. Returns the aggregate and an :class:`OrganizationSeeded`.
        """
        org = cls(
            _token=_CREATION_TOKEN,
            _id=organization_id,
            _name=name,
            _slug=slug,
            _status=OrganizationStatus.ACTIVE,
            _created_at=now,
            _updated_at=now,
        )
        event = OrganizationSeeded(aggregate_id=organization_id.value, name=name, slug=slug)
        return org, [event]

    @classmethod
    def rehydrate(
        cls,
        *,
        organization_id: OrganizationId,
        name: OrganizationName,
        slug: OrganizationSlug,
        status: OrganizationStatus,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> Organization:
        """Reconstruct the aggregate from persistence (no re-validation, no events)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=organization_id,
            _name=name,
            _slug=slug,
            _status=status,
            _created_at=created_at,
            _updated_at=updated_at,
            _deleted_at=deleted_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> OrganizationId:
        return self._id

    @property
    def name(self) -> OrganizationName:
        return self._name

    @property
    def slug(self) -> OrganizationSlug:
        return self._slug

    @property
    def status(self) -> OrganizationStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def version(self) -> int:
        return self._version

    def is_active(self) -> bool:
        """Whether the organization is currently operational."""
        return self._status is OrganizationStatus.ACTIVE

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def suspend(self, *, now: datetime) -> list[DomainEvent]:
        """Suspend the organization (administrative break-glass)."""
        if self._status is OrganizationStatus.SUSPENDED:
            raise OrganizationSuspendedError("The organization is already suspended.")
        self._status = OrganizationStatus.SUSPENDED
        self._touch(now)
        return [OrganizationSuspended(aggregate_id=self._id.value)]

    def reactivate(self, *, now: datetime) -> list[DomainEvent]:
        """Reactivate a suspended organization."""
        if self._status is not OrganizationStatus.SUSPENDED:
            raise OrganizationNotSuspendedError("The organization is not suspended.")
        self._status = OrganizationStatus.ACTIVE
        self._touch(now)
        return [OrganizationReactivated(aggregate_id=self._id.value)]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _touch(self, now: datetime) -> None:
        """Advance the change timestamp and optimistic-concurrency version once."""
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Organization) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Organization(id={self._id!r}, slug={self._slug.value!r}, status={self._status})"


@dataclass(slots=True, eq=False, repr=False)
class StaffMembership:
    """A user's staff role over the organization — the authorization fact.

    Lifecycle ``PENDING → ACTIVE → REVOKED``. Authorization is decided *only* by
    an ACTIVE membership (never by any Identity user attribute). Carries the audit
    trail — who invited/created/updated/revoked it and when — to support a future
    audit log. Equality/hashing is by :class:`StaffMembershipId`.
    """

    _token: InitVar[object]
    _id: StaffMembershipId
    _organization_id: OrganizationId
    _user_id: StaffUserId
    _role: StaffRole
    _status: MembershipStatus
    _created_at: datetime
    _updated_at: datetime
    _created_by: StaffUserId | None = None
    _updated_by: StaffUserId | None = None
    _invited_by: StaffUserId | None = None
    _revoked_by: StaffUserId | None = None
    _invited_at: datetime | None = None
    _accepted_at: datetime | None = None
    _revoked_at: datetime | None = None
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError(
                "StaffMembership must be created via a factory "
                "(pending_from_invitation / activate_for_owner) or rehydrate()."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def pending_from_invitation(
        cls,
        *,
        membership_id: StaffMembershipId,
        organization_id: OrganizationId,
        user_id: StaffUserId,
        role: StaffRole,
        invited_by: StaffUserId,
        invited_at: datetime,
        now: datetime,
    ) -> StaffMembership:
        """Create a PENDING membership recorded from an accepted-invitation flow.

        Emits no event by itself: the meaningful fact is activation, produced by
        :meth:`activate`. Kept distinct so the accept use case can create then
        activate in one transaction while the audit trail records the invitation.
        """
        return cls(
            _token=_CREATION_TOKEN,
            _id=membership_id,
            _organization_id=organization_id,
            _user_id=user_id,
            _role=role,
            _status=MembershipStatus.PENDING,
            _created_at=now,
            _updated_at=now,
            _created_by=invited_by,
            _invited_by=invited_by,
            _invited_at=invited_at,
        )

    @classmethod
    def activate_for_owner(
        cls,
        *,
        membership_id: StaffMembershipId,
        organization_id: OrganizationId,
        user_id: StaffUserId,
        now: datetime,
    ) -> tuple[StaffMembership, list[DomainEvent]]:
        """Create an immediately-ACTIVE OWNER membership (the bootstrap path).

        The sanctioned break-glass for the first owner (management command). No
        invitation precedes it, so there is no ``invited_by``; the membership is
        self-created and active at once. Returns a :class:`StaffMembershipActivated`.
        """
        membership = cls(
            _token=_CREATION_TOKEN,
            _id=membership_id,
            _organization_id=organization_id,
            _user_id=user_id,
            _role=StaffRole.OWNER,
            _status=MembershipStatus.ACTIVE,
            _created_at=now,
            _updated_at=now,
            _created_by=user_id,
            _accepted_at=now,
        )
        event = StaffMembershipActivated(
            aggregate_id=membership_id.value,
            organization_id=organization_id,
            user_id=user_id,
            role=StaffRole.OWNER,
        )
        return membership, [event]

    @classmethod
    def rehydrate(
        cls,
        *,
        membership_id: StaffMembershipId,
        organization_id: OrganizationId,
        user_id: StaffUserId,
        role: StaffRole,
        status: MembershipStatus,
        created_at: datetime,
        updated_at: datetime,
        created_by: StaffUserId | None = None,
        updated_by: StaffUserId | None = None,
        invited_by: StaffUserId | None = None,
        revoked_by: StaffUserId | None = None,
        invited_at: datetime | None = None,
        accepted_at: datetime | None = None,
        revoked_at: datetime | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> StaffMembership:
        """Reconstruct the aggregate from persistence (no re-validation, no events)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=membership_id,
            _organization_id=organization_id,
            _user_id=user_id,
            _role=role,
            _status=status,
            _created_at=created_at,
            _updated_at=updated_at,
            _created_by=created_by,
            _updated_by=updated_by,
            _invited_by=invited_by,
            _revoked_by=revoked_by,
            _invited_at=invited_at,
            _accepted_at=accepted_at,
            _revoked_at=revoked_at,
            _deleted_at=deleted_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> StaffMembershipId:
        return self._id

    @property
    def organization_id(self) -> OrganizationId:
        return self._organization_id

    @property
    def user_id(self) -> StaffUserId:
        return self._user_id

    @property
    def role(self) -> StaffRole:
        return self._role

    @property
    def status(self) -> MembershipStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def created_by(self) -> StaffUserId | None:
        return self._created_by

    @property
    def updated_by(self) -> StaffUserId | None:
        return self._updated_by

    @property
    def invited_by(self) -> StaffUserId | None:
        return self._invited_by

    @property
    def revoked_by(self) -> StaffUserId | None:
        return self._revoked_by

    @property
    def invited_at(self) -> datetime | None:
        return self._invited_at

    @property
    def accepted_at(self) -> datetime | None:
        return self._accepted_at

    @property
    def revoked_at(self) -> datetime | None:
        return self._revoked_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def version(self) -> int:
        return self._version

    def is_active(self) -> bool:
        """Whether this membership currently grants staff access."""
        return self._status is MembershipStatus.ACTIVE

    def has_role(self, *roles: StaffRole) -> bool:
        """Whether this membership is ACTIVE and carries one of ``roles``."""
        return self.is_active() and self._role in roles

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def activate(self, *, accepted_by: StaffUserId, now: datetime) -> list[DomainEvent]:
        """Transition a PENDING membership to ACTIVE (invitation accepted)."""
        if self._status is MembershipStatus.ACTIVE:
            raise MembershipAlreadyActiveError("The membership is already active.")
        if self._status is not MembershipStatus.PENDING:
            raise MembershipNotPendingError("Only a pending membership can be activated.")
        self._status = MembershipStatus.ACTIVE
        self._accepted_at = now
        self._touch(now, by=accepted_by)
        return [
            StaffMembershipActivated(
                aggregate_id=self._id.value,
                organization_id=self._organization_id,
                user_id=self._user_id,
                role=self._role,
            )
        ]

    def change_role(
        self, new_role: StaffRole, *, changed_by: StaffUserId, now: datetime
    ) -> list[DomainEvent]:
        """Change the role of an ACTIVE membership."""
        if self._status is MembershipStatus.REVOKED:
            raise MembershipAlreadyRevokedError("A revoked membership's role cannot be changed.")
        if self._status is not MembershipStatus.ACTIVE:
            raise MembershipNotPendingError("Only an active membership's role can be changed.")
        old_role = self._role
        if new_role is old_role:
            return []
        self._role = new_role
        self._touch(now, by=changed_by)
        return [
            StaffMembershipRoleChanged(
                aggregate_id=self._id.value,
                organization_id=self._organization_id,
                user_id=self._user_id,
                old_role=old_role,
                new_role=new_role,
                changed_by=changed_by,
            )
        ]

    def revoke(self, *, revoked_by: StaffUserId, now: datetime) -> list[DomainEvent]:
        """Revoke the membership, removing staff access."""
        if self._status is MembershipStatus.REVOKED:
            raise MembershipAlreadyRevokedError("The membership is already revoked.")
        self._status = MembershipStatus.REVOKED
        self._revoked_at = now
        self._revoked_by = revoked_by
        self._touch(now, by=revoked_by)
        return [
            StaffMembershipRevoked(
                aggregate_id=self._id.value,
                organization_id=self._organization_id,
                user_id=self._user_id,
                revoked_by=revoked_by,
            )
        ]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _touch(self, now: datetime, *, by: StaffUserId | None = None) -> None:
        """Advance the change timestamp/version and record who made the change."""
        self._updated_at = now
        if by is not None:
            self._updated_by = by
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StaffMembership) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"StaffMembership(id={self._id!r}, user_id={self._user_id!r}, "
            f"role={self._role}, status={self._status})"
        )


@dataclass(slots=True, eq=False, repr=False)
class StaffInvitation:
    """A pending, email-based grant of a staff role, awaiting acceptance.

    Only its SHA-256 token *hash* is ever held (:class:`InvitationTokenHash`); the
    raw secret lives solely in the emailed link. Lifecycle: issued → accepted |
    revoked | (implicitly) expired. Single-use: it can be accepted at most once.
    Equality/hashing is by :class:`StaffInvitationId`.
    """

    _token: InitVar[object]
    _id: StaffInvitationId
    _organization_id: OrganizationId
    _email: StaffEmail
    _role: StaffRole
    _token_hash: InvitationTokenHash
    _expires_at: datetime
    _invited_by: StaffUserId
    _created_at: datetime
    _updated_at: datetime
    _accepted_at: datetime | None = None
    _revoked_at: datetime | None = None
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError(
                "StaffInvitation must be created via StaffInvitation.issue() or rehydrate()."
            )

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def issue(
        cls,
        *,
        invitation_id: StaffInvitationId,
        organization_id: OrganizationId,
        email: StaffEmail,
        role: StaffRole,
        token_hash: InvitationTokenHash,
        raw_token: str,
        invited_by: StaffUserId,
        policy: InvitationExpiryPolicy,
        now: datetime,
    ) -> tuple[StaffInvitation, list[DomainEvent]]:
        """Issue a new invitation, stamping expiry from the injected policy.

        Returns the aggregate and a :class:`StaffInvitationIssued`. The raw token
        the ``token_hash`` derives from is minted outside the domain and emailed;
        the domain only ever sees the hash.
        """
        expires_at = policy.expires_at(now)
        invitation = cls(
            _token=_CREATION_TOKEN,
            _id=invitation_id,
            _organization_id=organization_id,
            _email=email,
            _role=role,
            _token_hash=token_hash,
            _expires_at=expires_at,
            _invited_by=invited_by,
            _created_at=now,
            _updated_at=now,
        )
        event = StaffInvitationIssued(
            aggregate_id=invitation_id.value,
            organization_id=organization_id,
            email=email,
            role=role,
            invited_by=invited_by,
            expires_at=expires_at,
            raw_token=raw_token,
        )
        return invitation, [event]

    @classmethod
    def rehydrate(
        cls,
        *,
        invitation_id: StaffInvitationId,
        organization_id: OrganizationId,
        email: StaffEmail,
        role: StaffRole,
        token_hash: InvitationTokenHash,
        expires_at: datetime,
        invited_by: StaffUserId,
        created_at: datetime,
        updated_at: datetime,
        accepted_at: datetime | None = None,
        revoked_at: datetime | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> StaffInvitation:
        """Reconstruct the aggregate from persistence (no re-validation, no events)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=invitation_id,
            _organization_id=organization_id,
            _email=email,
            _role=role,
            _token_hash=token_hash,
            _expires_at=expires_at,
            _invited_by=invited_by,
            _created_at=created_at,
            _updated_at=updated_at,
            _accepted_at=accepted_at,
            _revoked_at=revoked_at,
            _deleted_at=deleted_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> StaffInvitationId:
        return self._id

    @property
    def organization_id(self) -> OrganizationId:
        return self._organization_id

    @property
    def email(self) -> StaffEmail:
        return self._email

    @property
    def role(self) -> StaffRole:
        return self._role

    @property
    def token_hash(self) -> InvitationTokenHash:
        return self._token_hash

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    @property
    def invited_by(self) -> StaffUserId:
        return self._invited_by

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def accepted_at(self) -> datetime | None:
        return self._accepted_at

    @property
    def revoked_at(self) -> datetime | None:
        return self._revoked_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def version(self) -> int:
        return self._version

    def is_pending(self) -> bool:
        """Whether the invitation is still open (neither accepted nor revoked)."""
        return self._accepted_at is None and self._revoked_at is None

    def is_expired(self, *, policy: InvitationExpiryPolicy, now: datetime) -> bool:
        """Whether the invitation's validity window has lapsed at ``now``."""
        return policy.is_expired(expires_at=self._expires_at, now=now)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def accept(
        self,
        *,
        accepted_by: StaffUserId,
        policy: InvitationExpiryPolicy,
        now: datetime,
    ) -> list[DomainEvent]:
        """Accept the invitation, guarding single-use, revocation, and expiry.

        Verifying that the *presented raw token* hashes to this invitation's
        ``token_hash`` is an application-layer concern (it needs the hasher port);
        the domain guards the invitation's own state and validity window here.
        """
        if self._revoked_at is not None:
            raise InvitationRevokedError("The invitation was revoked and cannot be accepted.")
        if self._accepted_at is not None:
            raise InvitationAlreadyAcceptedError("The invitation has already been accepted.")
        if self.is_expired(policy=policy, now=now):
            raise InvitationExpiredError("The invitation has expired and cannot be accepted.")
        self._accepted_at = now
        self._touch(now)
        return [
            StaffInvitationAccepted(
                aggregate_id=self._id.value,
                organization_id=self._organization_id,
                accepted_by=accepted_by,
                role=self._role,
            )
        ]

    def revoke(self, *, revoked_by: StaffUserId, now: datetime) -> list[DomainEvent]:
        """Revoke a still-pending invitation before it is accepted."""
        if self._accepted_at is not None:
            raise InvitationAlreadyAcceptedError("An accepted invitation cannot be revoked.")
        if self._revoked_at is not None:
            raise InvitationRevokedError("The invitation is already revoked.")
        self._revoked_at = now
        self._touch(now)
        return [
            StaffInvitationRevoked(
                aggregate_id=self._id.value,
                organization_id=self._organization_id,
                revoked_by=revoked_by,
            )
        ]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _touch(self, now: datetime) -> None:
        """Advance the change timestamp and optimistic-concurrency version once."""
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StaffInvitation) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"StaffInvitation(id={self._id!r}, email={self._email.value!r}, "
            f"role={self._role}, pending={self.is_pending()})"
        )
