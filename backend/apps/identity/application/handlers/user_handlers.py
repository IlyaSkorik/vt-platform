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
    ConfirmEmailVerificationCommand,
    DeleteUserCommand,
    GrantConsentCommand,
    LockUserCommand,
    RegisterUserCommand,
    RequestEmailVerificationCommand,
    RequestPasswordResetCommand,
    ResetPasswordCommand,
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
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidInputError,
    InvalidVerificationTokenError,
    PhoneAlreadyInUseError,
    UserNotFoundError,
    translate_domain_errors,
)
from apps.identity.application.interfaces import (
    Clock,
    ConsentJournal,
    EmailGateway,
    PasswordHasher,
    UserRepository,
    UuidGenerator,
    VerificationTokenService,
)
from apps.identity.domain.entities import User
from apps.identity.domain.events import ConsentType
from apps.identity.domain.exceptions import ValueObjectValidationError
from apps.identity.domain.policies import (
    ConsentPolicy,
    EmailVerificationPolicy,
    PasswordPolicy,
    PasswordResetPolicy,
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
    "ConfirmEmailVerificationHandler",
    "DeleteUserHandler",
    "GrantConsentHandler",
    "LockUserHandler",
    "RegisterUserHandler",
    "RequestEmailVerificationHandler",
    "RequestPasswordResetHandler",
    "ResetPasswordHandler",
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
        raise UserNotFoundError("Пользователь не найден.")
    return user


def _parse_consent_type(raw: str | None) -> ConsentType:
    """Map a raw consent-type string to a :class:`ConsentType`, defaulting to ToS."""
    if raw is None:
        return ConsentType.TERMS_OF_SERVICE
    try:
        return ConsentType(raw)
    except ValueError as exc:
        raise InvalidInputError("Неизвестный тип согласия.") from exc


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
        consents: ConsentJournal,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._password_policy = password_policy
        self._clock = clock
        self._uuids = uuids
        self._consents = consents

    def handle(self, command: RegisterUserCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        with translate_domain_errors():
            email = Email(command.email)
            full_name = FullName.of(command.first_name, command.last_name, command.middle_name)
            phone = PhoneNumber(command.phone) if command.phone is not None else None
            locale = Locale(command.locale) if command.locale is not None else Locale.default()
            timezone = Timezone(command.timezone) if command.timezone is not None else Timezone.utc()
            # Strength is a domain rule, validated on the plaintext before hashing.
            self._password_policy.enforce(command.password)

        if self._users.exists_by_email(email):
            raise EmailAlreadyInUseError("Эта почта уже занята.")
        if phone is not None and self._users.exists_by_phone(phone):
            raise PhoneAlreadyInUseError("Этот телефон уже занят.")

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
        # The journal is written after the account is stored and before anything else
        # happens with it: the record has to name a user that exists, and no data may
        # be processed under a consent that was never recorded (LEGAL-001 §13.3).
        for acceptance in command.consents:
            self._consents.grant(
                user_id=user.id.json(),
                consent_type=acceptance.consent_type,
                version=acceptance.version,
                granted_at=now,
            )
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
    * **Email verification is a login gate.** A registered-but-unverified account
      is refused with :class:`EmailNotVerifiedError` (IDN-001) so it cannot
      establish a session until it confirms its address; ``is_email_verified``
      still travels out on the DTO for the edge. Locked/deleted accounts are
      refused separately with :class:`AccountInactiveError`.
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
            raise InvalidCredentialsError("Неверный адрес электронной почты или пароль") from exc

        user = self._users.get_by_email(email)
        if user is None:
            self._password_hasher.verify(command.password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError("Неверный адрес электронной почты или пароль")
        if not self._password_hasher.verify(command.password, user.password_hash):
            raise InvalidCredentialsError("Неверный адрес электронной почты или пароль")
        if user.is_deleted() or user.is_locked(now):
            raise AccountInactiveError("С этой учетной записью невозможно войти в систему")
        if not user.is_email_verified():
            raise EmailNotVerifiedError("Пожалуйста, подтвердите свой адрес электронной почты перед входом в систему")

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


class ConfirmEmailVerificationHandler:
    """Use case: confirm an email from the signed token carried by the emailed link.

    The edge-facing counterpart to :class:`VerifyEmailHandler`: it accepts only the
    opaque token, verifies its integrity through the
    :class:`~apps.identity.application.interfaces.VerificationTokenService` (which
    yields the account id and the instant the link was issued), then applies the
    same domain verification — honouring the link timeout owned by
    :class:`~apps.identity.domain.policies.EmailVerificationPolicy`. A tampered or
    malformed token raises
    :class:`~apps.identity.application.exceptions.InvalidVerificationTokenError`; a
    stale (expired) link surfaces as the domain's verification-expired error.
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        tokens: VerificationTokenService,
        email_verification_policy: EmailVerificationPolicy,
        clock: Clock,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._policy = email_verification_policy
        self._clock = clock

    def handle(self, command: ConfirmEmailVerificationCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        decoded = self._tokens.verify(command.token)
        user = self._users.get(decoded.user_id)
        if user is None:
            raise UserNotFoundError("Пользователь не найден.")
        with translate_domain_errors():
            events = user.verify_email(policy=self._policy, sent_at=decoded.issued_at, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class RequestEmailVerificationHandler:
    """Use case: (re)send an email-verification link to the account owning an address.

    Public and unauthenticated (a user gated out of login by an unverified email
    must still be able to request a fresh link). Looks the account up **by email**
    and, when it exists and is still unverified, mints a fresh link and dispatches
    the email through the :class:`~apps.identity.application.interfaces.EmailGateway`.

    Deliberately **anti-enumeration** (API-000 §26): a malformed, unknown, deleted,
    or already-verified address is a silent no-op that returns ``None`` — never an
    error — so a caller cannot distinguish "registered & unverified" from any other
    case by the response. Sending is a side effect this handler performs directly
    (rather than returning an event) because it is itself the reaction to a resend
    *request*, not a state change of the aggregate.
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        tokens: VerificationTokenService,
        email_gateway: EmailGateway,
        clock: Clock,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._email_gateway = email_gateway
        self._clock = clock

    def handle(self, command: RequestEmailVerificationCommand) -> None:
        now = self._clock.utcnow()
        try:
            email = Email(command.email)
        except ValueObjectValidationError:
            return  # A malformed address identifies no account; no-op (no enumeration).
        user = self._users.get_by_email(email)
        if user is None or user.is_deleted() or user.is_email_verified():
            return  # Unknown/deleted/already-verified: silent no-op (no enumeration).
        link = self._tokens.issue_link(user_id=user.id, issued_at=now)
        self._email_gateway.send_verification_email(
            email=user.email,
            full_name=user.full_name,
            verification_url=link,
            locale=user.locale,
        )


class RequestPasswordResetHandler:
    """Use case: begin password recovery by emailing a reset link (IDN-004).

    Public and unauthenticated (a user who forgot their password cannot sign in).
    Looks the account up **by email** and, when it exists, is active, and has a
    **verified** address (the reset link must reach a mailbox the platform trusts —
    IDN-002), mints a fresh, time-stamped link through a
    :class:`~apps.identity.application.interfaces.VerificationTokenService` and
    dispatches it via the :class:`~apps.identity.application.interfaces.EmailGateway`,
    together with the ``expires_at`` deadline the
    :class:`~apps.identity.domain.policies.PasswordResetPolicy` defines.

    Deliberately **anti-enumeration** (API-000 §26), mirroring
    :class:`RequestEmailVerificationHandler`: a malformed, unknown, deleted, or
    unverified-email address is a silent no-op that returns ``None`` — never an
    error — so a caller cannot distinguish a recoverable account from any other
    case by the response.
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        tokens: VerificationTokenService,
        email_gateway: EmailGateway,
        reset_policy: PasswordResetPolicy,
        clock: Clock,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._email_gateway = email_gateway
        self._reset_policy = reset_policy
        self._clock = clock

    def handle(self, command: RequestPasswordResetCommand) -> None:
        now = self._clock.utcnow()
        try:
            email = Email(command.email)
        except ValueObjectValidationError:
            return  # A malformed address identifies no account; no-op (no enumeration).
        user = self._users.get_by_email(email)
        if user is None or user.is_deleted() or not user.is_email_verified():
            return  # Unknown/deleted/unverified: silent no-op (no enumeration).
        # Present the deadline in the account's own zone (storage stays UTC): the
        # emailed time reads naturally to the recipient rather than as a UTC instant.
        expires_at = (now + self._reset_policy.reset_timeout).astimezone(user.timezone.zone_info)
        link = self._tokens.issue_link(user_id=user.id, issued_at=now)
        self._email_gateway.send_password_reset(
            email=user.email,
            full_name=user.full_name,
            reset_url=link,
            expires_at=expires_at,
            locale=user.locale,
        )


class ResetPasswordHandler:
    """Use case: set a new password from the emailed reset link (IDN-004).

    The unauthenticated counterpart to :class:`ChangePasswordHandler`: it accepts
    the opaque reset token plus the new password, verifies the token's integrity
    through the :class:`~apps.identity.application.interfaces.VerificationTokenService`
    (which yields the account id and the instant the link was issued), enforces
    password strength (:class:`~apps.identity.domain.policies.PasswordPolicy`),
    hashes the plaintext, and applies the domain reset — honouring the link timeout
    owned by :class:`~apps.identity.domain.policies.PasswordResetPolicy` and
    stamping the account's credential cut-off so every outstanding session is
    revoked.

    A tampered or malformed token — or one naming an account that no longer exists —
    raises :class:`~apps.identity.application.exceptions.InvalidVerificationTokenError`
    (``422``), never revealing whether the account exists; a stale (expired) link
    surfaces as the domain's verification-expired error (``410``).
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        tokens: VerificationTokenService,
        password_hasher: PasswordHasher,
        password_policy: PasswordPolicy,
        reset_policy: PasswordResetPolicy,
        clock: Clock,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._password_hasher = password_hasher
        self._password_policy = password_policy
        self._reset_policy = reset_policy
        self._clock = clock

    def handle(self, command: ResetPasswordCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        decoded = self._tokens.verify(command.token)
        user = self._users.get(decoded.user_id)
        if user is None:
            # A valid signature for a vanished account: treat as an unusable token
            # rather than a 404, so the reset edge never confirms account existence.
            raise InvalidVerificationTokenError("Ссылка для смены пароля недействительна или уже использована.")
        with translate_domain_errors():
            self._password_policy.enforce(command.new_password)
        password_hash = self._password_hasher.hash(command.new_password)
        with translate_domain_errors():
            events = user.reset_password(
                password_hash,
                policy=self._reset_policy,
                issued_at=decoded.issued_at,
                now=now,
            )
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class ChangeEmailHandler:
    """Use case: replace the account's email address (resets verification).

    Re-asks for the current password. The address is the account's recovery
    channel, so moving it is as consequential as changing the password itself and
    is refused on the strength of a session alone.
    """

    def __init__(self, *, users: UserRepository, password_hasher: PasswordHasher, clock: Clock) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._clock = clock

    def handle(self, command: ChangeEmailCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        if not self._password_hasher.verify(command.current_password, user.password_hash):
            raise InvalidCredentialsError("Текущий пароль указан неверно.")
        with translate_domain_errors():
            new_email = Email(command.new_email)
        owner = self._users.get_by_email(new_email)
        if owner is not None and owner.id != user.id:
            raise EmailAlreadyInUseError("Эта почта уже занята.")
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
            raise PhoneAlreadyInUseError("Этот телефон уже занят.")
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
    """Use case: the account holder changes their own password.

    The current password is verified first, so a session left open on somebody
    else's machine cannot be turned into a permanent takeover. A reset driven by
    an emailed token, where the holder has no current password to give, is
    :class:`ResetPasswordHandler`'s job instead — and that one revokes every
    issued credential, because it starts from no session at all. This one does
    not: the holder is already signed in and stays signed in.
    """

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
        if not self._password_hasher.verify(command.current_password, user.password_hash):
            raise InvalidCredentialsError("Текущий пароль указан неверно.")
        with translate_domain_errors():
            self._password_policy.enforce(command.new_password)
        password_hash = self._password_hasher.hash(command.new_password)
        with translate_domain_errors():
            events = user.change_password(password_hash, now=now)
        self._users.save(user)
        return OperationResultDto(user=UserDto.from_user(user, now=now), events=tuple(events))


class GrantConsentHandler:
    """Use case: record acceptance of a versioned consent document."""

    def __init__(self, *, users: UserRepository, consent_policy: ConsentPolicy, clock: Clock) -> None:
        self._users = users
        self._policy = consent_policy
        self._clock = clock

    def handle(self, command: GrantConsentCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        user = _load_user(self._users, command.user_id)
        consent_type = _parse_consent_type(command.consent_type)
        with translate_domain_errors():
            version = ConsentVersion(command.consent_version)
            events = user.grant_consent(version, policy=self._policy, now=now, consent_type=consent_type)
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


class CurrentUserHandler:
    """Use case: retrieve the current authenticated user's details."""

    def __init__(self, *, users: UserRepository, clock: Clock) -> None:
        self._users = users
        self._clock = clock

    def handle(self, user_id: str) -> UserDto:
        user = _load_user(self._users, user_id)
        now = self._clock.utcnow()
        return UserDto.from_user(user, now=now)
