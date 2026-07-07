"""Command handlers (use cases) for the Identity & Access bounded context.

One handler per command. A handler is a thin **orchestrator**: it holds no
business rules of its own (those live in the domain) and no persistence details
(those live in infrastructure). It depends only on application **ports**
(:mod:`apps.identity.application.interfaces`) and injected domain **policies**,
and it follows one shape:

    1. resolve the current instant from the :class:`Clock`;
    2. load the aggregate (or, for registration, mint identity + hash + create);
    3. build validated value objects from the command's raw fields;
    4. execute the aggregate's behaviour, **receiving** the domain events;
    5. persist the aggregate through the :class:`UserRepository`;
    6. return an :class:`OperationResultDto` carrying the new state **and** the
       collected events.

**Events are collected, never published.** A handler returns the events the
domain produced; a future Unit of Work will commit the aggregate and forward them
to the outbox / event dispatcher (ARCH-001 §4.8). Because the events already ride
out on the result, that future refactor needs no change to these signatures.

**Errors are translated, never swallowed.** Domain-touching steps run inside
:func:`~apps.identity.application.exceptions.translate_domain_errors`, which
re-raises domain errors as application errors (preserving the cause). Cross-
aggregate uniqueness and "not found" are application concerns raised directly
here.

This module imports nothing from infrastructure, presentation, or Django.
"""

from __future__ import annotations

from typing import Final

from apps.identity.application.commands import (
    AuthenticateUserCommand,
    ChangeEmailCommand,
    ChangePasswordCommand,
    ChangePhoneCommand,
    DeleteUserCommand,
    GrantConsentCommand,
    LockUserCommand,
    RegisterUserCommand,
    RestoreUserCommand,
    UnlockUserCommand,
    VerifyEmailCommand,
    VerifyPhoneCommand,
    WithdrawConsentCommand,
)
from apps.identity.application.dto import OperationResultDto, UserDto
from apps.identity.application.exceptions import (
    AccountInactiveError,
    EmailAlreadyInUseError,
    InvalidCredentialsError,
    InvalidInputError,
    PhoneAlreadyInUseError,
    UserNotFoundError,
    translate_domain_errors,
)
from apps.identity.application.interfaces import (
    Clock,
    PasswordHasher,
    UserRepository,
    UuidGenerator,
)
from apps.identity.domain.entities import User
from apps.identity.domain.events import ConsentType
from apps.identity.domain.exceptions import ValueObjectValidationError
from apps.identity.domain.policies import (
    ConsentPolicy,
    EmailVerificationPolicy,
    PasswordPolicy,
    PhoneVerificationPolicy,
)
from apps.identity.domain.value_objects import (
    ConsentVersion,
    Email,
    FullName,
    Locale,
    PasswordHash,
    PhoneNumber,
    Timezone,
    UserId,
)

__all__ = [
    "AuthenticateUserHandler",
    "ChangeEmailHandler",
    "ChangePasswordHandler",
    "ChangePhoneHandler",
    "DeleteUserHandler",
    "GrantConsentHandler",
    "LockUserHandler",
    "RegisterUserHandler",
    "RestoreUserHandler",
    "UnlockUserHandler",
    "VerifyEmailHandler",
    "VerifyPhoneHandler",
    "WithdrawConsentHandler",
]


#: A syntactically valid Argon2 digest matching **no** password. When an account
#: is not found, the login handler still runs a verify against this so an
#: unknown-email request costs the same wall-clock time as a wrong-password one,
#: denying a timing side-channel that would otherwise enumerate accounts (§26).
_DUMMY_PASSWORD_HASH: Final = PasswordHash.from_hash(
    "$argon2id$v=19$m=65536,t=3,p=4$R7qaszSliB96sR+y7FYb+A$BO8zHWZUEAXhQCI8eVsi8l2TvtUZoLUUrgzsL4jcOBE"
)


def _load_user(users: UserRepository, raw_user_id: str) -> User:
    """Resolve ``raw_user_id`` and load the aggregate, or raise application errors.

    A malformed id becomes :class:`InvalidInputError`; a well-formed id with no
    stored user becomes :class:`UserNotFoundError`.
    """
    with translate_domain_errors():
        user_id = UserId.from_string(raw_user_id)
    user = users.get(user_id)
    if user is None:
        raise UserNotFoundError(f"No user found with id {raw_user_id!r}.")
    return user


def _parse_consent_type(raw: str | None) -> ConsentType:
    """Map a raw consent-type string to a :class:`ConsentType`, defaulting to ToS."""
    if raw is None:
        return ConsentType.TERMS_OF_SERVICE
    try:
        return ConsentType(raw)
    except ValueError as exc:
        raise InvalidInputError(f"Unknown consent type {raw!r}.") from exc


class RegisterUserHandler:
    """Use case: create a brand-new account.

    Validates password strength (a domain :class:`PasswordPolicy`) and value
    objects, enforces email/phone uniqueness across accounts, hashes the password,
    mints a UUID v7 identity, and creates the aggregate.
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
        password_policy: PasswordPolicy,
        clock: Clock,
        uuids: UuidGenerator,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._password_policy = password_policy
        self._clock = clock
        self._uuids = uuids

    def handle(self, command: RegisterUserCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        with translate_domain_errors():
            email = Email(command.email)
            full_name = FullName.of(command.first_name, command.last_name, command.middle_name)
            phone = PhoneNumber(command.phone) if command.phone is not None else None
            locale = Locale(command.locale) if command.locale is not None else Locale.default()
            timezone = (
                Timezone(command.timezone) if command.timezone is not None else Timezone.utc()
            )
            # Strength is a domain rule, validated on the plaintext before hashing.
            self._password_policy.enforce(command.password)

        if self._users.exists_by_email(email):
            raise EmailAlreadyInUseError(f"Email {email.masked()} is already registered.")
        if phone is not None and self._users.exists_by_phone(phone):
            raise PhoneAlreadyInUseError("The phone number is already registered.")

        password_hash = self._password_hasher.hash(command.password)
        user_id = UserId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            user, events = User.register(
                user_id=user_id,
                email=email,
                full_name=full_name,
                password_hash=password_hash,
                now=now,
                phone=phone,
                locale=locale,
                timezone=timezone,
            )
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class AuthenticateUserHandler:
    """Use case: verify credentials and confirm the account may sign in (login).

    A **read-only** use case: it loads the account, verifies the submitted password
    through the :class:`PasswordHasher` port, and confirms the account is neither
    locked nor deleted. It never mutates the aggregate and emits no domain events —
    issuing the session's JWTs is a delivery concern handled by the presentation/
    infrastructure edge, outside this handler.

    Security posture (API-000 §26, API-001 §4.4):

    * **No account enumeration.** An unknown email, a malformed email, and a wrong
      password all raise the same :class:`InvalidCredentialsError`; the unknown/
      malformed paths still run a verify against a dummy hash so they cost the same
      time as a real one.
    * **Email verification is not a login gate.** A registered-but-unverified
      account *can* sign in; ``is_email_verified`` travels out on the DTO so the
      edge can gate *sensitive* actions later (IDN-001). Only locked/deleted
      accounts are refused here (:class:`AccountInactiveError`).
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._clock = clock

    def handle(self, command: AuthenticateUserCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        try:
            email = Email(command.email)
        except ValueObjectValidationError as exc:
            # A malformed email identifies no account; equalize timing, then fail
            # with the same generic error as a wrong password (no enumeration).
            self._password_hasher.verify(command.password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError("Invalid email or password.") from exc

        user = self._users.get_by_email(email)
        if user is None:
            self._password_hasher.verify(command.password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError("Invalid email or password.")
        if not self._password_hasher.verify(command.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        if user.is_deleted() or user.is_locked(now):
            raise AccountInactiveError("This account cannot sign in.")

        return OperationResultDto(user=UserDto.from_user(user, now=now), events=())


class VerifyEmailHandler:
    """Use case: confirm ownership of the account's current email address."""

    def __init__(
        self,
        *,
        users: UserRepository,
        email_verification_policy: EmailVerificationPolicy,
        clock: Clock,
    ) -> None:
        self._users = users
        self._policy = email_verification_policy
        self._clock = clock

    def handle(self, command: VerifyEmailCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            events = user.verify_email(policy=self._policy, sent_at=command.sent_at, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class ChangeEmailHandler:
    """Use case: replace the account's email address (resets verification)."""

    def __init__(self, *, users: UserRepository, clock: Clock) -> None:
        self._users = users
        self._clock = clock

    def handle(self, command: ChangeEmailCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            new_email = Email(command.new_email)
        owner = self._users.get_by_email(new_email)
        if owner is not None and owner.id != user.id:
            raise EmailAlreadyInUseError(f"Email {new_email.masked()} is already registered.")
        with translate_domain_errors():
            events = user.change_email(new_email, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class ChangePhoneHandler:
    """Use case: set or replace the account's phone number (resets verification)."""

    def __init__(self, *, users: UserRepository, clock: Clock) -> None:
        self._users = users
        self._clock = clock

    def handle(self, command: ChangePhoneCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            new_phone = PhoneNumber(command.new_phone)
        owner = self._users.get_by_phone(new_phone)
        if owner is not None and owner.id != user.id:
            raise PhoneAlreadyInUseError("The phone number is already registered.")
        with translate_domain_errors():
            events = user.change_phone(new_phone, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class VerifyPhoneHandler:
    """Use case: confirm ownership of the account's current phone number."""

    def __init__(
        self,
        *,
        users: UserRepository,
        phone_verification_policy: PhoneVerificationPolicy,
        clock: Clock,
    ) -> None:
        self._users = users
        self._policy = phone_verification_policy
        self._clock = clock

    def handle(self, command: VerifyPhoneCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            events = user.verify_phone(policy=self._policy, issued_at=command.issued_at, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class ChangePasswordHandler:
    """Use case: set a new password (strength-checked, then hashed)."""

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
        password_policy: PasswordPolicy,
        clock: Clock,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._password_policy = password_policy
        self._clock = clock

    def handle(self, command: ChangePasswordCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            self._password_policy.enforce(command.new_password)
        password_hash = self._password_hasher.hash(command.new_password)
        with translate_domain_errors():
            events = user.change_password(password_hash, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class GrantConsentHandler:
    """Use case: record acceptance of a versioned consent document."""

    def __init__(
        self, *, users: UserRepository, consent_policy: ConsentPolicy, clock: Clock
    ) -> None:
        self._users = users
        self._policy = consent_policy
        self._clock = clock

    def handle(self, command: GrantConsentCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        consent_type = _parse_consent_type(command.consent_type)
        with translate_domain_errors():
            version = ConsentVersion(command.consent_version)
            events = user.grant_consent(
                version, policy=self._policy, now=now, consent_type=consent_type
            )
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class WithdrawConsentHandler:
    """Use case: revoke the account's currently-active consent."""

    def __init__(self, *, users: UserRepository, clock: Clock) -> None:
        self._users = users
        self._clock = clock

    def handle(self, command: WithdrawConsentCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        consent_type = _parse_consent_type(command.consent_type)
        with translate_domain_errors():
            events = user.withdraw_consent(now=now, consent_type=consent_type)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class LockUserHandler:
    """Use case: lock the account, blocking authentication."""

    def __init__(self, *, users: UserRepository, clock: Clock) -> None:
        self._users = users
        self._clock = clock

    def handle(self, command: LockUserCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            events = user.lock(reason=command.reason, until=command.until, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class UnlockUserHandler:
    """Use case: release an active lock on the account."""

    def __init__(self, *, users: UserRepository, clock: Clock) -> None:
        self._users = users
        self._clock = clock

    def handle(self, command: UnlockUserCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            events = user.unlock(reason=command.reason, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class DeleteUserHandler:
    """Use case: soft-delete the account (reversible, retained for audit)."""

    def __init__(self, *, users: UserRepository, clock: Clock) -> None:
        self._users = users
        self._clock = clock

    def handle(self, command: DeleteUserCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            events = user.soft_delete(now=now, reason=command.reason)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class RestoreUserHandler:
    """Use case: reactivate a soft-deleted account."""

    def __init__(self, *, users: UserRepository, clock: Clock) -> None:
        self._users = users
        self._clock = clock

    def handle(self, command: RestoreUserCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        with translate_domain_errors():
            events = user.restore(now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))
