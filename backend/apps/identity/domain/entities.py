"""Domain entities for the Identity & Access bounded context.

The :class:`User` aggregate root (ARCH-001 §7.2, §13.4) — the framework-free
business core of a user account. It **owns all state and behaviour** and is the
sole guardian of the account's invariants: every rule about when an email may be
verified, when a lock applies, or whether a deleted account may be touched lives
here, not in a service, serializer, or model.

This is **pure domain code** (ARCH-001 §4.1, §7.2): standard library only — no
Django, no DRF, no ORM, no clock, no IO, no global state. Time is always supplied
by the caller (``now``) so the aggregate is deterministic and trivially testable.

Design contract:

* **No direct construction.** The dataclass constructor is guarded; build a
  ``User`` only via :meth:`User.register` (a brand-new account, which validates
  invariants and emits :class:`~apps.identity.domain.events.UserRegistered`) or
  :meth:`User.rehydrate` (reconstruction from persistence, which re-validates
  nothing and emits nothing).
* **Encapsulated state.** All fields are private; only read-only properties are
  exposed. Every value is an immutable value object or a primitive, so no mutable
  state can leak out.
* **Behaviour returns events, never publishes them.** Each business method
  validates invariants, consults the relevant policy where one applies, mutates
  internal state, bumps ``updated_at`` and the optimistic-concurrency ``version``,
  and returns the ``list`` of domain events describing what happened. Dispatching
  those events is an outer-layer concern.
* **Invalid transitions raise** typed
  :class:`~apps.identity.domain.exceptions.UserStateError` subclasses — they are
  never silently ignored.

Policy boundaries (why not every policy is consulted here): password *strength*
(:class:`~apps.identity.domain.policies.PasswordPolicy`) is validated on the
plaintext upstream, before hashing, since the domain only ever sees a
:class:`~apps.identity.domain.value_objects.PasswordHash`; lock escalation
(:class:`~apps.identity.domain.policies.AccountLockPolicy`) and session lifetimes
(:class:`~apps.identity.domain.policies.SessionPolicy`) are computed in the
application layer because the aggregate deliberately does not hold failed-attempt
counters or session records. This aggregate consults
:class:`~apps.identity.domain.policies.ConsentPolicy`,
:class:`~apps.identity.domain.policies.EmailVerificationPolicy`, and
:class:`~apps.identity.domain.policies.PhoneVerificationPolicy`, whose inputs it
owns.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from datetime import UTC, datetime
from typing import Final

from .events import (
    ConsentGranted,
    ConsentType,
    ConsentWithdrawn,
    DomainEvent,
    EmailChanged,
    EmailVerified,
    LocaleChanged,
    PasswordChanged,
    PhoneChanged,
    PhoneVerified,
    TimezoneChanged,
    UserDeleted,
    UserLocked,
    UserRegistered,
    UserRenamed,
    UserRestored,
    UserUnlocked,
)
from .exceptions import (
    ConsentNotGrantedError,
    DirectConstructionError,
    EmailAlreadyVerifiedError,
    EmailNotChangedError,
    PhoneAlreadyVerifiedError,
    PhoneNotChangedError,
    PhoneNotSetError,
    StaleConsentError,
    UserDeletedError,
    UserNotDeletedError,
    UserNotLockedError,
    VerificationExpiredError,
)
from .policies import ConsentPolicy, EmailVerificationPolicy, PhoneVerificationPolicy
from .value_objects import (
    ConsentVersion,
    Email,
    FullName,
    Locale,
    PasswordHash,
    PhoneNumber,
    Timezone,
    UserId,
)

__all__ = ["User"]

#: Opaque capability token proving construction went through a factory. Held only
#: by this module, so :meth:`User.register`/:meth:`User.rehydrate` can pass it and
#: nobody else can (short of importing a private name).
_CREATION_TOKEN: Final = object()

#: Platform defaults applied at registration when the caller omits a preference.
#: Precomputed (not called inline) so they are constant, immutable, and shared.
_DEFAULT_LOCALE: Final = Locale.default()
_DEFAULT_TIMEZONE: Final = Timezone.utc()

#: Sentinel ``locked_until`` for an indefinite (permanent) lock. ``None`` already
#: means "not locked", so a permanent lock needs a value that is always in the
#: future; the maximum representable aware instant serves exactly that role.
_PERMANENT_LOCK: Final = datetime.max.replace(tzinfo=UTC)


@dataclass(slots=True, eq=False, repr=False)
class User:
    """The user-account aggregate root of the Identity context.

    Construct via :meth:`register` or :meth:`rehydrate` only — never directly.
    State is private and exposed through read-only properties; behaviour is the
    ``change_*``/``verify_*``/lifecycle methods, each of which returns the domain
    events it produced. Equality and hashing are by :class:`UserId` alone: two
    ``User`` objects denote the same account iff they share an identity, regardless
    of their current field values.
    """

    # ``_token`` is an InitVar (never stored): it reaches __post_init__ to prove
    # the instance came from a factory, then is discarded.
    _token: InitVar[object]
    _id: UserId
    _email: Email
    _full_name: FullName
    _locale: Locale
    _timezone: Timezone
    _password_hash: PasswordHash
    _created_at: datetime
    _updated_at: datetime
    _phone: PhoneNumber | None = None
    _consent_version: ConsentVersion | None = None
    _email_verified_at: datetime | None = None
    _phone_verified_at: datetime | None = None
    _locked_until: datetime | None = None
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise DirectConstructionError("User must be created via User.register() or User.rehydrate(), not by calling the constructor directly.")

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def register(
        cls,
        *,
        user_id: UserId,
        email: Email,
        full_name: FullName,
        password_hash: PasswordHash,
        now: datetime,
        phone: PhoneNumber | None = None,
        locale: Locale = _DEFAULT_LOCALE,
        timezone: Timezone = _DEFAULT_TIMEZONE,
    ) -> tuple[User, list[DomainEvent]]:
        """Create a brand-new account and the fact that it was registered.

        Every argument is an already-valid value object (each validated its own
        input on construction), so registration itself only assembles them into a
        consistent initial state: unverified contact details, no consent yet, not
        locked, not deleted, ``version`` 1, and ``created_at == updated_at == now``.

        Returns the new aggregate together with ``[UserRegistered]`` — the caller
        persists the aggregate and dispatches the events atomically.
        """
        user = cls(
            _token=_CREATION_TOKEN,
            _id=user_id,
            _email=email,
            _full_name=full_name,
            _locale=locale,
            _timezone=timezone,
            _password_hash=password_hash,
            _created_at=now,
            _updated_at=now,
            _phone=phone,
        )
        events: list[DomainEvent] = [
            UserRegistered(
                aggregate_id=user_id,
                email=email,
                full_name=full_name,
                locale=locale,
                occurred_at=now,
            )
        ]
        return user, events

    @classmethod
    def rehydrate(
        cls,
        *,
        user_id: UserId,
        email: Email,
        full_name: FullName,
        locale: Locale,
        timezone: Timezone,
        password_hash: PasswordHash,
        created_at: datetime,
        updated_at: datetime,
        version: int,
        phone: PhoneNumber | None = None,
        consent_version: ConsentVersion | None = None,
        email_verified_at: datetime | None = None,
        phone_verified_at: datetime | None = None,
        locked_until: datetime | None = None,
        deleted_at: datetime | None = None,
    ) -> User:
        """Reconstruct an existing aggregate from persisted state.

        A pure hydration step: it re-runs **no** business workflow, enforces **no**
        transition rule, emits **no** events, and leaves ``version`` exactly as
        stored (never incremented). The invariants were established when the state
        was first written; replaying them here would be wrong (it could reject data
        that is already durable) and would fabricate spurious events.
        """
        return cls(
            _token=_CREATION_TOKEN,
            _id=user_id,
            _email=email,
            _full_name=full_name,
            _locale=locale,
            _timezone=timezone,
            _password_hash=password_hash,
            _created_at=created_at,
            _updated_at=updated_at,
            _phone=phone,
            _consent_version=consent_version,
            _email_verified_at=email_verified_at,
            _phone_verified_at=phone_verified_at,
            _locked_until=locked_until,
            _deleted_at=deleted_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Read-only state
    # ------------------------------------------------------------------

    @property
    def id(self) -> UserId:
        """The account's immutable identity."""
        return self._id

    @property
    def email(self) -> Email:
        """The current email address (may be unverified)."""
        return self._email

    @property
    def phone(self) -> PhoneNumber | None:
        """The current phone number, or ``None`` if none is set."""
        return self._phone

    @property
    def full_name(self) -> FullName:
        """The account holder's name."""
        return self._full_name

    @property
    def locale(self) -> Locale:
        """The preferred locale."""
        return self._locale

    @property
    def timezone(self) -> Timezone:
        """The preferred timezone (storage stays UTC regardless)."""
        return self._timezone

    @property
    def password_hash(self) -> PasswordHash:
        """The stored password digest (opaque; its own repr is redacted)."""
        return self._password_hash

    @property
    def consent_version(self) -> ConsentVersion | None:
        """The consent version currently accepted, or ``None`` if none is active."""
        return self._consent_version

    @property
    def created_at(self) -> datetime:
        """When the account was registered."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """When the aggregate last changed."""
        return self._updated_at

    @property
    def email_verified_at(self) -> datetime | None:
        """When the current email was verified, or ``None`` if unverified."""
        return self._email_verified_at

    @property
    def phone_verified_at(self) -> datetime | None:
        """When the current phone was verified, or ``None`` if unverified/unset."""
        return self._phone_verified_at

    @property
    def locked_until(self) -> datetime | None:
        """The lock expiry instant; ``None`` if unlocked, far-future if permanent."""
        return self._locked_until

    @property
    def deleted_at(self) -> datetime | None:
        """When the account was soft-deleted, or ``None`` if active."""
        return self._deleted_at

    @property
    def version(self) -> int:
        """Optimistic-concurrency version; bumped once per successful mutation."""
        return self._version

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_deleted(self) -> bool:
        """Whether the account is soft-deleted."""
        return self._deleted_at is not None

    def is_email_verified(self) -> bool:
        """Whether the current email address has been verified."""
        return self._email_verified_at is not None

    def is_phone_verified(self) -> bool:
        """Whether the current phone number has been verified."""
        return self._phone_verified_at is not None

    def is_locked(self, now: datetime) -> bool:
        """Whether the account is locked at ``now`` (temporary locks auto-expire)."""
        return self._locked_until is not None and now < self._locked_until

    def requires_consent(self, policy: ConsentPolicy) -> bool:
        """Whether the user must (re-)consent under ``policy``.

        ``True`` when no consent is recorded or the accepted version is older than
        the version currently in force.
        """
        return self._consent_version is None or not policy.is_current(self._consent_version)

    def can_login(self, *, now: datetime) -> bool:
        """Whether the account may authenticate at ``now``.

        Requires an active (non-deleted), unlocked account with a verified email.
        Consent gating is evaluated separately via :meth:`requires_consent`, as it
        depends on the currently-in-force policy.
        """
        return not self.is_deleted() and not self.is_locked(now) and self.is_email_verified()

    # ------------------------------------------------------------------
    # Contact details
    # ------------------------------------------------------------------

    def change_email(self, new_email: Email, *, now: datetime) -> list[DomainEvent]:
        """Replace the email address, resetting its verified status.

        Guards against a no-op change specifically because the reset of
        verification is a real side effect that must not fire accidentally.
        """
        self._ensure_active()
        if new_email == self._email:
            raise EmailNotChangedError("The new email is identical to the current one.")
        events: list[DomainEvent] = [EmailChanged(aggregate_id=self._id, email=new_email, occurred_at=now)]
        self._email = new_email
        self._email_verified_at = None
        self._touch(now)
        return events

    def verify_email(self, *, policy: EmailVerificationPolicy, sent_at: datetime, now: datetime) -> list[DomainEvent]:
        """Mark the current email verified, honouring the verification-link timeout."""
        self._ensure_active()
        if self.is_email_verified():
            raise EmailAlreadyVerifiedError("The email address is already verified.")
        if policy.is_verification_expired(sent_at, now):
            raise VerificationExpiredError("The email verification link has expired.")
        events: list[DomainEvent] = [EmailVerified(aggregate_id=self._id, email=self._email, occurred_at=now)]
        self._email_verified_at = now
        self._touch(now)
        return events

    def ensure_email_unverified(self) -> None:
        """Guard that the email is not yet verified, else raise (a read-only check).

        Lets a use case that (re)issues a verification challenge refuse early — with
        the same :class:`~apps.identity.domain.exceptions.EmailAlreadyVerifiedError`
        :meth:`verify_email` would raise — without mutating the aggregate or
        emitting an event, since sending a fresh link is not a state change.
        """
        self._ensure_active()
        if self.is_email_verified():
            raise EmailAlreadyVerifiedError("The email address is already verified.")

    def change_phone(self, new_phone: PhoneNumber, *, now: datetime) -> list[DomainEvent]:
        """Set or replace the phone number, resetting its verified status."""
        self._ensure_active()
        if self._phone is not None and new_phone == self._phone:
            raise PhoneNotChangedError("The new phone number is identical to the current one.")
        events: list[DomainEvent] = [PhoneChanged(aggregate_id=self._id, phone=new_phone, occurred_at=now)]
        self._phone = new_phone
        self._phone_verified_at = None
        self._touch(now)
        return events

    def verify_phone(self, *, policy: PhoneVerificationPolicy, issued_at: datetime, now: datetime) -> list[DomainEvent]:
        """Mark the current phone verified, honouring the code lifetime."""
        self._ensure_active()
        if self._phone is None:
            raise PhoneNotSetError("Cannot verify a phone number: none is set.")
        if self.is_phone_verified():
            raise PhoneAlreadyVerifiedError("The phone number is already verified.")
        if policy.is_code_expired(issued_at, now):
            raise VerificationExpiredError("The phone verification code has expired.")
        events: list[DomainEvent] = [PhoneVerified(aggregate_id=self._id, phone=self._phone, occurred_at=now)]
        self._phone_verified_at = now
        self._touch(now)
        return events

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def change_password(self, new_password_hash: PasswordHash, *, now: datetime) -> list[DomainEvent]:
        """Replace the stored password digest.

        The domain accepts an already-computed :class:`PasswordHash`; plaintext
        strength (``PasswordPolicy``) and reuse are validated upstream, before
        hashing, so the aggregate never sees or compares a plaintext or a hash.
        """
        self._ensure_active()
        events: list[DomainEvent] = [PasswordChanged(aggregate_id=self._id, occurred_at=now)]
        self._password_hash = new_password_hash
        self._touch(now)
        return events

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------

    def grant_consent(
        self,
        consent_version: ConsentVersion,
        *,
        policy: ConsentPolicy,
        now: datetime,
        consent_type: ConsentType = ConsentType.TERMS_OF_SERVICE,
    ) -> list[DomainEvent]:
        """Record acceptance of a consent document version.

        Consults :class:`ConsentPolicy` to refuse granting a version older than the
        one currently in force (an outdated grant would be legally meaningless).
        """
        self._ensure_active()
        if not policy.is_current(consent_version):
            raise StaleConsentError(f"Cannot grant consent version {consent_version} older than the current version.")
        events: list[DomainEvent] = [
            ConsentGranted(
                aggregate_id=self._id,
                consent_type=consent_type,
                consent_version=consent_version,
                occurred_at=now,
            )
        ]
        self._consent_version = consent_version
        self._touch(now)
        return events

    def withdraw_consent(self, *, now: datetime, consent_type: ConsentType = ConsentType.TERMS_OF_SERVICE) -> list[DomainEvent]:
        """Revoke the currently-active consent."""
        self._ensure_active()
        if self._consent_version is None:
            raise ConsentNotGrantedError("There is no active consent to withdraw.")
        withdrawn = self._consent_version
        events: list[DomainEvent] = [
            ConsentWithdrawn(
                aggregate_id=self._id,
                consent_type=consent_type,
                consent_version=withdrawn,
                occurred_at=now,
            )
        ]
        self._consent_version = None
        self._touch(now)
        return events

    # ------------------------------------------------------------------
    # Lock / unlock
    # ------------------------------------------------------------------

    def lock(self, *, reason: str, until: datetime | None, now: datetime) -> list[DomainEvent]:
        """Lock the account, blocking authentication.

        ``until`` bounds a temporary lock; ``None`` requests an indefinite
        (permanent) lock. The deadline and escalation are decided upstream by
        :class:`~apps.identity.domain.policies.AccountLockPolicy` (which owns the
        failed-attempt counters this aggregate deliberately does not hold).
        """
        self._ensure_active()
        events: list[DomainEvent] = [UserLocked(aggregate_id=self._id, reason=reason, locked_until=until, occurred_at=now)]
        self._locked_until = _PERMANENT_LOCK if until is None else until
        self._touch(now)
        return events

    def unlock(self, *, reason: str, now: datetime) -> list[DomainEvent]:
        """Release an active lock."""
        self._ensure_active()
        if not self.is_locked(now):
            raise UserNotLockedError("The account is not currently locked.")
        events: list[DomainEvent] = [UserUnlocked(aggregate_id=self._id, reason=reason, occurred_at=now)]
        self._locked_until = None
        self._touch(now)
        return events

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def soft_delete(self, *, now: datetime, reason: str | None = None) -> list[DomainEvent]:
        """Soft-delete the account (reversible; retains the record for audit)."""
        self._ensure_active()
        events: list[DomainEvent] = [UserDeleted(aggregate_id=self._id, reason=reason, occurred_at=now)]
        self._deleted_at = now
        self._touch(now)
        return events

    def restore(self, *, now: datetime) -> list[DomainEvent]:
        """Reactivate a soft-deleted account."""
        if self._deleted_at is None:
            raise UserNotDeletedError("The account is not deleted; nothing to restore.")
        events: list[DomainEvent] = [UserRestored(aggregate_id=self._id, occurred_at=now)]
        self._deleted_at = None
        self._touch(now)
        return events

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def rename(self, new_name: FullName, *, now: datetime) -> list[DomainEvent]:
        """Change the account holder's name."""
        self._ensure_active()
        events: list[DomainEvent] = [UserRenamed(aggregate_id=self._id, full_name=new_name, occurred_at=now)]
        self._full_name = new_name
        self._touch(now)
        return events

    def change_locale(self, new_locale: Locale, *, now: datetime) -> list[DomainEvent]:
        """Change the preferred locale."""
        self._ensure_active()
        events: list[DomainEvent] = [LocaleChanged(aggregate_id=self._id, locale=new_locale, occurred_at=now)]
        self._locale = new_locale
        self._touch(now)
        return events

    def change_timezone(self, new_timezone: Timezone, *, now: datetime) -> list[DomainEvent]:
        """Change the preferred timezone."""
        self._ensure_active()
        events: list[DomainEvent] = [TimezoneChanged(aggregate_id=self._id, timezone=new_timezone, occurred_at=now)]
        self._timezone = new_timezone
        self._touch(now)
        return events

    # ------------------------------------------------------------------
    # Identity semantics
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        # Never expose the password hash.
        return (
            f"User(id={self._id.json()!r}, email={self._email.value!r}, "
            f"version={self._version}, email_verified={self.is_email_verified()}, "
            f"locked_until={self._locked_until!r}, deleted={self.is_deleted()})"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_active(self) -> None:
        """Guard: forbid mutating a soft-deleted account (restore is the exception)."""
        if self._deleted_at is not None:
            raise UserDeletedError(f"User {self._id} is deleted; operation not permitted.")

    def _touch(self, now: datetime) -> None:
        """Stamp the mutation time and advance the optimistic-concurrency version."""
        self._updated_at = now
        self._version += 1
