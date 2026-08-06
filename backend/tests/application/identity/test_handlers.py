"""Unit tests for the Identity command handlers (use cases).

Framework-free, database-free, clock-free (ARCH-001 §28.2): every dependency is
an in-memory fake (:mod:`tests.application.identity.fakes`), time is a frozen
:class:`FakeClock`, and domain policies are used for real. Each handler is tested
for its happy path, the events it collects, persistence, and every error branch
(uniqueness, not-found, invalid input, state conflict, weak password).
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from apps.identity.application.commands import (
    ChangeEmailCommand,
    ChangePasswordCommand,
    ChangePhoneCommand,
    ConfirmEmailVerificationCommand,
    DeleteUserCommand,
    GrantConsentCommand,
    LockUserCommand,
    RegisterUserCommand,
    RequestEmailVerificationCommand,
    RestoreUserCommand,
    UnlockUserCommand,
    VerifyEmailCommand,
    VerifyPhoneCommand,
    WithdrawConsentCommand,
)
from apps.identity.application.events import SendVerificationEmailOnUserRegistered
from apps.identity.application.exceptions import (
    EmailAlreadyInUseError,
    InvalidCredentialsError,
    InvalidInputError,
    InvalidVerificationTokenError,
    PhoneAlreadyInUseError,
    UserNotFoundError,
    UserStateConflictError,
    WeakPasswordError,
)
from apps.identity.application.handlers import (
    ChangeEmailHandler,
    ChangePasswordHandler,
    ChangePhoneHandler,
    ConfirmEmailVerificationHandler,
    DeleteUserHandler,
    GrantConsentHandler,
    LockUserHandler,
    RegisterUserHandler,
    RequestEmailVerificationHandler,
    RestoreUserHandler,
    UnlockUserHandler,
    VerifyEmailHandler,
    VerifyPhoneHandler,
    WithdrawConsentHandler,
)
from apps.identity.domain.entities import User
from apps.identity.domain.events import (
    ConsentGranted,
    ConsentType,
    ConsentWithdrawn,
    EmailChanged,
    EmailVerified,
    PasswordChanged,
    PhoneChanged,
    PhoneVerified,
    UserDeleted,
    UserLocked,
    UserRegistered,
    UserRestored,
    UserUnlocked,
)
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
    PasswordHash,
    PhoneNumber,
    UserId,
)
from tests.application.identity.fakes import (
    NOW,
    FakeClock,
    FakeConsentJournal,
    FakeEmailGateway,
    FakePasswordHasher,
    FakeUserRepository,
    FakeUuidGenerator,
    FakeVerificationTokenService,
)

STRONG_PASSWORD = "V3ry$ecurePass!"
VALID_HASH = PasswordHash.from_hash("$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA")
PASSWORD_POLICY = PasswordPolicy()
EMAIL_POLICY = EmailVerificationPolicy()
PHONE_POLICY = PhoneVerificationPolicy()
CONSENT_POLICY = ConsentPolicy(current_version=ConsentVersion("1.0"))


#: The plaintext behind :data:`KNOWN_HASH` — what a seeded account's holder would
#: type when a use case re-asks for the password they already have.
CURRENT_PASSWORD = "TheirOldPass!7"
KNOWN_HASH = FakePasswordHasher().hash(CURRENT_PASSWORD)


def make_user(*, email: str = "member@example.com", phone: str | None = None, password_hash: PasswordHash = VALID_HASH) -> User:
    """Build a fresh (registered, unverified) ``User`` for seeding a repository."""
    user, _ = User.register(
        user_id=UserId.generate(),
        email=Email(email),
        full_name=FullName.of("Ivan", "Petrov", "Ivanovich"),
        password_hash=password_hash,
        now=NOW,
        phone=PhoneNumber(phone) if phone is not None else None,
    )
    return user


def unknown_user_id() -> str:
    """A syntactically valid UUID v7 that is not stored in any repository."""
    return UserId.generate().json()


# ---------------------------------------------------------------------------
# RegisterUserHandler
# ---------------------------------------------------------------------------


class TestRegisterUserHandler:
    def _handler(self, repo: FakeUserRepository, hasher: FakePasswordHasher, uuids: FakeUuidGenerator) -> RegisterUserHandler:
        return RegisterUserHandler(
            users=repo,
            password_hasher=hasher,
            password_policy=PASSWORD_POLICY,
            clock=FakeClock(),
            uuids=uuids,
            consents=FakeConsentJournal(),
        )

    def test_register_success_with_all_optionals(self) -> None:
        repo, hasher, uuids = FakeUserRepository(), FakePasswordHasher(), FakeUuidGenerator()
        command = RegisterUserCommand(
            email="New.User@Example.com",
            password=STRONG_PASSWORD,
            first_name="Anna",
            last_name="Ivanova",
            middle_name="Petrovna",
            phone="+375291234567",
            locale="en-US",
            timezone="Europe/Moscow",
        )

        result = self._handler(repo, hasher, uuids).handle(command)

        assert result.user.email == "new.user@example.com"
        assert result.user.phone == "+375291234567"
        assert result.user.middle_name == "Petrovna"
        assert result.user.locale == "en-US"
        assert result.user.timezone == "Europe/Moscow"
        assert result.user.version == 1
        assert not result.user.is_email_verified
        assert len(result.events) == 1
        assert isinstance(result.events[0], UserRegistered)
        assert hasher.hashed == [STRONG_PASSWORD]
        assert len(uuids.issued) == 1
        assert repo.saved and repo.saved[0].id.json() == result.user.id

    def test_register_success_with_defaults(self) -> None:
        repo, hasher, uuids = FakeUserRepository(), FakePasswordHasher(), FakeUuidGenerator()
        command = RegisterUserCommand(
            email="minimal@example.com",
            password=STRONG_PASSWORD,
            first_name="Boris",
            last_name="Sidorov",
        )

        result = self._handler(repo, hasher, uuids).handle(command)

        assert result.user.phone is None
        assert result.user.middle_name is None
        assert result.user.locale == "ru-RU"  # platform default
        assert result.user.timezone == "UTC"  # platform default
        assert result.user.is_locked is False
        assert result.user.locked_until is None
        assert result.user.consent_version is None

    def test_register_rejects_duplicate_email(self) -> None:
        repo = FakeUserRepository()
        repo.seed(make_user(email="taken@example.com"))
        command = RegisterUserCommand(
            email="taken@example.com",
            password=STRONG_PASSWORD,
            first_name="Anna",
            last_name="Ivanova",
        )

        with pytest.raises(EmailAlreadyInUseError):
            self._handler(repo, FakePasswordHasher(), FakeUuidGenerator()).handle(command)

    def test_register_rejects_duplicate_phone(self) -> None:
        repo = FakeUserRepository()
        repo.seed(make_user(email="other@example.com", phone="+375291234567"))
        command = RegisterUserCommand(
            email="fresh@example.com",
            password=STRONG_PASSWORD,
            first_name="Anna",
            last_name="Ivanova",
            phone="+375291234567",
        )

        with pytest.raises(PhoneAlreadyInUseError):
            self._handler(repo, FakePasswordHasher(), FakeUuidGenerator()).handle(command)

    def test_register_rejects_weak_password(self) -> None:
        repo = FakeUserRepository()
        command = RegisterUserCommand(
            email="weak@example.com",
            password="short",
            first_name="Anna",
            last_name="Ivanova",
        )

        with pytest.raises(WeakPasswordError) as excinfo:
            self._handler(repo, FakePasswordHasher(), FakeUuidGenerator()).handle(command)
        assert excinfo.value.violations  # non-empty machine-readable reasons

    def test_register_rejects_invalid_email(self) -> None:
        repo = FakeUserRepository()
        command = RegisterUserCommand(
            email="not-an-email",
            password=STRONG_PASSWORD,
            first_name="Anna",
            last_name="Ivanova",
        )

        with pytest.raises(InvalidInputError):
            self._handler(repo, FakePasswordHasher(), FakeUuidGenerator()).handle(command)


# ---------------------------------------------------------------------------
# _load_user shared behaviour (via VerifyEmailHandler)
# ---------------------------------------------------------------------------


class TestLoadUser:
    def _handler(self, repo: FakeUserRepository) -> VerifyEmailHandler:
        return VerifyEmailHandler(users=repo, email_verification_policy=EMAIL_POLICY, clock=FakeClock())

    def test_missing_user_raises_not_found(self) -> None:
        repo = FakeUserRepository()
        command = VerifyEmailCommand(user_id=unknown_user_id(), sent_at=NOW)

        with pytest.raises(UserNotFoundError):
            self._handler(repo).handle(command)

    def test_malformed_user_id_raises_invalid_input(self) -> None:
        repo = FakeUserRepository()
        command = VerifyEmailCommand(user_id="not-a-uuid", sent_at=NOW)

        with pytest.raises(InvalidInputError):
            self._handler(repo).handle(command)


# ---------------------------------------------------------------------------
# VerifyEmailHandler
# ---------------------------------------------------------------------------


class TestVerifyEmailHandler:
    def _handler(self, repo: FakeUserRepository) -> VerifyEmailHandler:
        return VerifyEmailHandler(users=repo, email_verification_policy=EMAIL_POLICY, clock=FakeClock())

    def test_verifies_email(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = VerifyEmailCommand(user_id=user.id.json(), sent_at=NOW - timedelta(hours=1))

        result = self._handler(repo).handle(command)

        assert result.user.is_email_verified is True
        assert isinstance(result.events[0], EmailVerified)
        assert repo.saved[-1] is user

    def test_expired_link_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = VerifyEmailCommand(user_id=user.id.json(), sent_at=NOW - timedelta(hours=25))

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(command)
        assert excinfo.value.domain_code == "VerificationExpiredError"


# ---------------------------------------------------------------------------
# ConfirmEmailVerificationHandler
# ---------------------------------------------------------------------------


class TestConfirmEmailVerificationHandler:
    def _handler(self, repo: FakeUserRepository, tokens: FakeVerificationTokenService) -> ConfirmEmailVerificationHandler:
        return ConfirmEmailVerificationHandler(
            users=repo,
            tokens=tokens,
            email_verification_policy=EMAIL_POLICY,
            clock=FakeClock(),
        )

    def test_confirms_email_from_token(self) -> None:
        repo = FakeUserRepository()
        tokens = FakeVerificationTokenService()
        user = repo.seed(make_user())
        tokens.issue_link(user_id=user.id, issued_at=NOW - timedelta(hours=1))
        token = tokens.links[0].split("token=")[1]

        result = self._handler(repo, tokens).handle(ConfirmEmailVerificationCommand(token=token))

        assert result.user.is_email_verified is True
        assert isinstance(result.events[0], EmailVerified)
        assert repo.saved[-1] is user

    def test_invalid_token_is_rejected(self) -> None:
        repo = FakeUserRepository()
        tokens = FakeVerificationTokenService()

        with pytest.raises(InvalidVerificationTokenError):
            self._handler(repo, tokens).handle(ConfirmEmailVerificationCommand(token="garbage"))

    def test_expired_link_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        tokens = FakeVerificationTokenService()
        user = repo.seed(make_user())
        tokens.issue_link(user_id=user.id, issued_at=NOW - timedelta(hours=25))
        token = tokens.links[0].split("token=")[1]

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo, tokens).handle(ConfirmEmailVerificationCommand(token=token))
        assert excinfo.value.domain_code == "VerificationExpiredError"

    def test_unknown_user_is_not_found(self) -> None:
        repo = FakeUserRepository()
        tokens = FakeVerificationTokenService()
        # Issue for a user that was never persisted.
        tokens.issue_link(user_id=UserId.generate(), issued_at=NOW)
        token = tokens.links[0].split("token=")[1]

        with pytest.raises(UserNotFoundError):
            self._handler(repo, tokens).handle(ConfirmEmailVerificationCommand(token=token))


# ---------------------------------------------------------------------------
# RequestEmailVerificationHandler
# ---------------------------------------------------------------------------


class TestRequestEmailVerificationHandler:
    def _handler(
        self,
        repo: FakeUserRepository,
        tokens: FakeVerificationTokenService,
        gateway: FakeEmailGateway,
    ) -> RequestEmailVerificationHandler:
        return RequestEmailVerificationHandler(users=repo, tokens=tokens, email_gateway=gateway, clock=FakeClock())

    def test_sends_a_fresh_verification_email(self) -> None:
        repo = FakeUserRepository()
        tokens = FakeVerificationTokenService()
        gateway = FakeEmailGateway()
        user = repo.seed(make_user(email="member@example.com"))

        self._handler(repo, tokens, gateway).handle(RequestEmailVerificationCommand(email="member@example.com"))

        assert len(gateway.verification_emails) == 1
        sent = gateway.verification_emails[0]
        assert sent.email == user.email
        assert sent.verification_url == tokens.links[-1]

    def test_no_op_when_already_verified(self) -> None:
        # Anti-enumeration + no-op: a verified address needs no link and must not
        # error (that would reveal the address is registered).
        repo = FakeUserRepository()
        tokens = FakeVerificationTokenService()
        gateway = FakeEmailGateway()
        user = make_user(email="member@example.com")
        user.verify_email(policy=EMAIL_POLICY, sent_at=NOW, now=NOW)
        repo.seed(user)

        self._handler(repo, tokens, gateway).handle(RequestEmailVerificationCommand(email="member@example.com"))

        assert gateway.verification_emails == []

    def test_no_op_for_unknown_email(self) -> None:
        # Anti-enumeration: an unregistered address is a silent no-op, not an error.
        repo = FakeUserRepository()
        tokens = FakeVerificationTokenService()
        gateway = FakeEmailGateway()

        self._handler(repo, tokens, gateway).handle(RequestEmailVerificationCommand(email="ghost@example.com"))

        assert gateway.verification_emails == []


# ---------------------------------------------------------------------------
# SendVerificationEmailOnUserRegistered (event side-effect)
# ---------------------------------------------------------------------------


class TestSendVerificationEmailOnUserRegistered:
    def test_registration_event_sends_verification_email(self) -> None:
        tokens = FakeVerificationTokenService()
        gateway = FakeEmailGateway()
        handler = SendVerificationEmailOnUserRegistered(email_gateway=gateway, tokens=tokens, clock=FakeClock())
        user, events = User.register(
            user_id=UserId.generate(),
            email=Email("new@example.com"),
            full_name=FullName.of("Ada", "Lovelace"),
            password_hash=VALID_HASH,
            now=NOW,
        )
        registered = events[0]
        assert isinstance(registered, UserRegistered)

        handler.handle(registered)

        assert len(gateway.verification_emails) == 1
        sent = gateway.verification_emails[0]
        assert sent.email == user.email
        assert sent.verification_url == tokens.links[-1]


# ---------------------------------------------------------------------------
# ChangeEmailHandler
# ---------------------------------------------------------------------------


class TestChangeEmailHandler:
    def _handler(self, repo: FakeUserRepository) -> ChangeEmailHandler:
        return ChangeEmailHandler(users=repo, password_hasher=FakePasswordHasher(), clock=FakeClock())

    def _seed(self, repo: FakeUserRepository, *, email: str) -> User:
        return repo.seed(make_user(email=email, password_hash=KNOWN_HASH))

    def _command(self, user: User, new_email: str, *, password: str = CURRENT_PASSWORD) -> ChangeEmailCommand:
        return ChangeEmailCommand(user_id=user.id.json(), new_email=new_email, current_password=password)

    def test_changes_email(self) -> None:
        repo = FakeUserRepository()
        user = self._seed(repo, email="old@example.com")

        result = self._handler(repo).handle(self._command(user, "brand.new@example.com"))

        assert result.user.email == "brand.new@example.com"
        assert result.user.is_email_verified is False
        assert isinstance(result.events[0], EmailChanged)

    def test_refuses_without_the_current_password(self) -> None:
        """The address is the recovery channel; a session alone must not move it."""
        repo = FakeUserRepository()
        user = self._seed(repo, email="old@example.com")

        with pytest.raises(InvalidCredentialsError):
            self._handler(repo).handle(self._command(user, "brand.new@example.com", password="not-it"))
        assert repo.get(user.id) is not None
        assert repo.get(user.id).email.value == "old@example.com"  # type: ignore[union-attr]

    def test_rejects_email_used_by_another_user(self) -> None:
        repo = FakeUserRepository()
        user = self._seed(repo, email="mine@example.com")
        repo.seed(make_user(email="theirs@example.com"))

        with pytest.raises(EmailAlreadyInUseError):
            self._handler(repo).handle(self._command(user, "theirs@example.com"))

    def test_same_email_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = self._seed(repo, email="same@example.com")

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(self._command(user, "same@example.com"))
        assert excinfo.value.domain_code == "EmailNotChangedError"


# ---------------------------------------------------------------------------
# ChangePhoneHandler
# ---------------------------------------------------------------------------


class TestChangePhoneHandler:
    def _handler(self, repo: FakeUserRepository) -> ChangePhoneHandler:
        return ChangePhoneHandler(users=repo, clock=FakeClock())

    def test_sets_phone(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = ChangePhoneCommand(user_id=user.id.json(), new_phone="+375291234567")

        result = self._handler(repo).handle(command)

        assert result.user.phone == "+375291234567"
        assert result.user.is_phone_verified is False
        assert isinstance(result.events[0], PhoneChanged)

    def test_rejects_phone_used_by_another_user(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user(email="a@example.com"))
        repo.seed(make_user(email="b@example.com", phone="+375291234567"))
        command = ChangePhoneCommand(user_id=user.id.json(), new_phone="+375291234567")

        with pytest.raises(PhoneAlreadyInUseError):
            self._handler(repo).handle(command)

    def test_same_phone_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user(phone="+375291234567"))
        command = ChangePhoneCommand(user_id=user.id.json(), new_phone="+375291234567")

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(command)
        assert excinfo.value.domain_code == "PhoneNotChangedError"


# ---------------------------------------------------------------------------
# VerifyPhoneHandler
# ---------------------------------------------------------------------------


class TestVerifyPhoneHandler:
    def _handler(self, repo: FakeUserRepository) -> VerifyPhoneHandler:
        return VerifyPhoneHandler(users=repo, phone_verification_policy=PHONE_POLICY, clock=FakeClock())

    def test_verifies_phone(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user(phone="+375291234567"))
        command = VerifyPhoneCommand(user_id=user.id.json(), issued_at=NOW - timedelta(minutes=1))

        result = self._handler(repo).handle(command)

        assert result.user.is_phone_verified is True
        assert isinstance(result.events[0], PhoneVerified)

    def test_no_phone_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = VerifyPhoneCommand(user_id=user.id.json(), issued_at=NOW)

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(command)
        assert excinfo.value.domain_code == "PhoneNotSetError"


# ---------------------------------------------------------------------------
# ChangePasswordHandler
# ---------------------------------------------------------------------------


class TestChangePasswordHandler:
    def _handler(self, repo: FakeUserRepository, hasher: FakePasswordHasher) -> ChangePasswordHandler:
        return ChangePasswordHandler(users=repo, password_hasher=hasher, password_policy=PASSWORD_POLICY, clock=FakeClock())

    def test_changes_password(self) -> None:
        repo, hasher = FakeUserRepository(), FakePasswordHasher()
        user = repo.seed(make_user(password_hash=KNOWN_HASH))
        command = ChangePasswordCommand(user_id=user.id.json(), current_password=CURRENT_PASSWORD, new_password=STRONG_PASSWORD)

        result = self._handler(repo, hasher).handle(command)

        assert isinstance(result.events[0], PasswordChanged)
        assert hasher.hashed == [STRONG_PASSWORD]
        assert result.user.version == user.version

    def test_refuses_a_wrong_current_password(self) -> None:
        """A session someone else is sitting in front of is not authorization."""
        repo, hasher = FakeUserRepository(), FakePasswordHasher()
        user = repo.seed(make_user(password_hash=KNOWN_HASH))
        command = ChangePasswordCommand(user_id=user.id.json(), current_password="not-it", new_password=STRONG_PASSWORD)

        with pytest.raises(InvalidCredentialsError):
            self._handler(repo, hasher).handle(command)
        # Nothing was hashed: the new password never got as far as the hasher.
        assert hasher.hashed == []

    def test_rejects_weak_password(self) -> None:
        repo, hasher = FakeUserRepository(), FakePasswordHasher()
        user = repo.seed(make_user(password_hash=KNOWN_HASH))
        command = ChangePasswordCommand(user_id=user.id.json(), current_password=CURRENT_PASSWORD, new_password="weak")

        with pytest.raises(WeakPasswordError):
            self._handler(repo, hasher).handle(command)


# ---------------------------------------------------------------------------
# GrantConsentHandler
# ---------------------------------------------------------------------------


class TestGrantConsentHandler:
    def _handler(self, repo: FakeUserRepository) -> GrantConsentHandler:
        return GrantConsentHandler(users=repo, consent_policy=CONSENT_POLICY, clock=FakeClock())

    def test_grants_consent_default_type(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = GrantConsentCommand(user_id=user.id.json(), consent_version="1.0")

        result = self._handler(repo).handle(command)

        assert result.user.consent_version == "1.0"
        event = result.events[0]
        assert isinstance(event, ConsentGranted)
        assert event.consent_type is ConsentType.TERMS_OF_SERVICE

    def test_grants_consent_explicit_type(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = GrantConsentCommand(user_id=user.id.json(), consent_version="1.1", consent_type="privacy_policy")

        result = self._handler(repo).handle(command)

        event = result.events[0]
        assert isinstance(event, ConsentGranted)
        assert event.consent_type is ConsentType.PRIVACY_POLICY

    def test_unknown_consent_type_is_invalid_input(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = GrantConsentCommand(user_id=user.id.json(), consent_version="1.0", consent_type="bogus")

        with pytest.raises(InvalidInputError):
            self._handler(repo).handle(command)

    def test_stale_consent_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = GrantConsentCommand(user_id=user.id.json(), consent_version="0.9")

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(command)
        assert excinfo.value.domain_code == "StaleConsentError"


# ---------------------------------------------------------------------------
# WithdrawConsentHandler
# ---------------------------------------------------------------------------


class TestWithdrawConsentHandler:
    def _handler(self, repo: FakeUserRepository) -> WithdrawConsentHandler:
        return WithdrawConsentHandler(users=repo, clock=FakeClock())

    def test_withdraws_active_consent(self) -> None:
        repo = FakeUserRepository()
        user = make_user()
        user.grant_consent(ConsentVersion("1.0"), policy=CONSENT_POLICY, now=NOW)
        repo.seed(user)
        command = WithdrawConsentCommand(user_id=user.id.json())

        result = self._handler(repo).handle(command)

        assert result.user.consent_version is None
        assert isinstance(result.events[0], ConsentWithdrawn)

    def test_without_active_consent_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = WithdrawConsentCommand(user_id=user.id.json())

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(command)
        assert excinfo.value.domain_code == "ConsentNotGrantedError"


# ---------------------------------------------------------------------------
# LockUserHandler / UnlockUserHandler
# ---------------------------------------------------------------------------


class TestLockUserHandler:
    def _handler(self, repo: FakeUserRepository) -> LockUserHandler:
        return LockUserHandler(users=repo, clock=FakeClock())

    def test_temporary_lock(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        until = NOW + timedelta(hours=1)
        command = LockUserCommand(user_id=user.id.json(), reason="too many attempts", until=until)

        result = self._handler(repo).handle(command)

        assert result.user.is_locked is True
        assert result.user.locked_until == until
        assert isinstance(result.events[0], UserLocked)

    def test_permanent_lock(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = LockUserCommand(user_id=user.id.json(), reason="fraud", until=None)

        result = self._handler(repo).handle(command)

        assert result.user.is_locked is True
        assert result.user.locked_until is not None  # far-future sentinel


class TestUnlockUserHandler:
    def _handler(self, repo: FakeUserRepository) -> UnlockUserHandler:
        return UnlockUserHandler(users=repo, clock=FakeClock())

    def test_unlocks_locked_user(self) -> None:
        repo = FakeUserRepository()
        user = make_user()
        user.lock(reason="temp", until=NOW + timedelta(hours=1), now=NOW)
        repo.seed(user)
        command = UnlockUserCommand(user_id=user.id.json(), reason="appeal upheld")

        result = self._handler(repo).handle(command)

        assert result.user.is_locked is False
        assert isinstance(result.events[0], UserUnlocked)

    def test_unlocking_active_user_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = UnlockUserCommand(user_id=user.id.json(), reason="noop")

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(command)
        assert excinfo.value.domain_code == "UserNotLockedError"


# ---------------------------------------------------------------------------
# DeleteUserHandler / RestoreUserHandler
# ---------------------------------------------------------------------------


class TestDeleteUserHandler:
    def _handler(self, repo: FakeUserRepository) -> DeleteUserHandler:
        return DeleteUserHandler(users=repo, clock=FakeClock())

    def test_soft_deletes_with_reason(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = DeleteUserCommand(user_id=user.id.json(), reason="user request")

        result = self._handler(repo).handle(command)

        assert result.user.is_deleted is True
        assert isinstance(result.events[0], UserDeleted)

    def test_soft_deletes_without_reason(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = DeleteUserCommand(user_id=user.id.json())

        result = self._handler(repo).handle(command)

        assert result.user.is_deleted is True

    def test_deleting_already_deleted_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = make_user()
        user.soft_delete(now=NOW)
        repo.seed(user)
        command = DeleteUserCommand(user_id=user.id.json())

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(command)
        assert excinfo.value.domain_code == "UserDeletedError"


class TestRestoreUserHandler:
    def _handler(self, repo: FakeUserRepository) -> RestoreUserHandler:
        return RestoreUserHandler(users=repo, clock=FakeClock())

    def test_restores_deleted_user(self) -> None:
        repo = FakeUserRepository()
        user = make_user()
        user.soft_delete(now=NOW)
        repo.seed(user)
        command = RestoreUserCommand(user_id=user.id.json())

        result = self._handler(repo).handle(command)

        assert result.user.is_deleted is False
        assert isinstance(result.events[0], UserRestored)

    def test_restoring_active_user_is_state_conflict(self) -> None:
        repo = FakeUserRepository()
        user = repo.seed(make_user())
        command = RestoreUserCommand(user_id=user.id.json())

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo).handle(command)
        assert excinfo.value.domain_code == "UserNotDeletedError"
