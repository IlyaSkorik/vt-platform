"""Unit tests for the password-reset use cases.

Framework-free, database-free: both handlers are exercised against the in-memory
fakes. Covers :class:`RequestPasswordResetHandler` (anti-enumeration + email
dispatch with the right expiry) and :class:`ResetPasswordHandler` (new password
set, sessions revoked via the credential cut-off, and the token/expiry/strength
failure modes).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from apps.identity.application.commands import RequestPasswordResetCommand, ResetPasswordCommand
from apps.identity.application.exceptions import (
    InvalidVerificationTokenError,
    UserStateConflictError,
    WeakPasswordError,
)
from apps.identity.application.handlers import RequestPasswordResetHandler, ResetPasswordHandler
from apps.identity.domain.entities import User
from apps.identity.domain.events import PasswordResetCompleted
from apps.identity.domain.policies import EmailVerificationPolicy, PasswordPolicy, PasswordResetPolicy
from apps.identity.domain.value_objects import Email, FullName, PasswordHash, UserId

from .fakes import (
    NOW,
    FakeClock,
    FakeEmailGateway,
    FakePasswordHasher,
    FakeUserRepository,
    FakeVerificationTokenService,
)

STRONG_PASSWORD = "V3ry$ecurePass!"
VALID_HASH = PasswordHash.from_hash("$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA")
RESET_POLICY = PasswordResetPolicy()
EMAIL_POLICY = EmailVerificationPolicy()


def _verified_user(*, email: str = "member@example.com") -> User:
    """A registered account with a verified email (eligible for reset)."""
    user, _ = User.register(
        user_id=UserId.generate(),
        email=Email(email),
        full_name=FullName.of("Ivan", "Petrov"),
        password_hash=VALID_HASH,
        now=NOW,
    )
    user.verify_email(policy=EMAIL_POLICY, sent_at=NOW, now=NOW)
    return user


class TestRequestPasswordResetHandler:
    def _handler(
        self,
        repo: FakeUserRepository,
        tokens: FakeVerificationTokenService,
        gateway: FakeEmailGateway,
    ) -> RequestPasswordResetHandler:
        return RequestPasswordResetHandler(
            users=repo,
            tokens=tokens,
            email_gateway=gateway,
            reset_policy=RESET_POLICY,
            clock=FakeClock(),
        )

    def test_sends_a_reset_link_with_expiry(self) -> None:
        repo, tokens, gateway = FakeUserRepository(), FakeVerificationTokenService(), FakeEmailGateway()
        user = repo.seed(_verified_user(email="member@example.com"))

        self._handler(repo, tokens, gateway).handle(RequestPasswordResetCommand(email="member@example.com"))

        assert len(gateway.password_resets) == 1
        sent = gateway.password_resets[0]
        assert sent.email == user.email
        assert sent.reset_url == tokens.links[-1]
        assert sent.expires_at == NOW + RESET_POLICY.reset_timeout

    def test_expiry_is_rendered_in_the_accounts_timezone(self) -> None:
        from datetime import timedelta as _td
        from zoneinfo import ZoneInfo

        from apps.identity.domain.value_objects import Timezone

        repo, tokens, gateway = FakeUserRepository(), FakeVerificationTokenService(), FakeEmailGateway()
        user, _ = User.register(
            user_id=UserId.generate(),
            email=Email("moscow@example.com"),
            full_name=FullName.of("Ivan", "Petrov"),
            password_hash=VALID_HASH,
            now=NOW,
            timezone=Timezone("Europe/Moscow"),
        )
        user.verify_email(policy=EMAIL_POLICY, sent_at=NOW, now=NOW)
        repo.seed(user)

        self._handler(repo, tokens, gateway).handle(RequestPasswordResetCommand(email="moscow@example.com"))

        sent = gateway.password_resets[0]
        # Same instant as UTC now + TTL, but carried in the account's zone (+03:00).
        assert sent.expires_at == NOW + RESET_POLICY.reset_timeout
        assert sent.expires_at.utcoffset() == _td(hours=3)
        assert sent.expires_at.tzinfo == ZoneInfo("Europe/Moscow")

    def test_no_op_for_unknown_email(self) -> None:
        repo, tokens, gateway = FakeUserRepository(), FakeVerificationTokenService(), FakeEmailGateway()

        self._handler(repo, tokens, gateway).handle(RequestPasswordResetCommand(email="ghost@example.com"))

        assert gateway.password_resets == []

    def test_no_op_for_unverified_email(self) -> None:
        # A reset link must reach a trusted mailbox; an unverified address is a
        # silent no-op (and anti-enumeration).
        repo, tokens, gateway = FakeUserRepository(), FakeVerificationTokenService(), FakeEmailGateway()
        user, _ = User.register(
            user_id=UserId.generate(),
            email=Email("unverified@example.com"),
            full_name=FullName.of("No", "Verify"),
            password_hash=VALID_HASH,
            now=NOW,
        )
        repo.seed(user)

        self._handler(repo, tokens, gateway).handle(RequestPasswordResetCommand(email="unverified@example.com"))

        assert gateway.password_resets == []

    def test_no_op_for_malformed_email(self) -> None:
        repo, tokens, gateway = FakeUserRepository(), FakeVerificationTokenService(), FakeEmailGateway()

        self._handler(repo, tokens, gateway).handle(RequestPasswordResetCommand(email="not-an-email"))

        assert gateway.password_resets == []

    def test_no_op_for_deleted_account(self) -> None:
        repo, tokens, gateway = FakeUserRepository(), FakeVerificationTokenService(), FakeEmailGateway()
        user = _verified_user(email="gone@example.com")
        user.soft_delete(now=NOW)
        repo.seed(user)

        self._handler(repo, tokens, gateway).handle(RequestPasswordResetCommand(email="gone@example.com"))

        assert gateway.password_resets == []


class TestResetPasswordHandler:
    def _handler(
        self,
        repo: FakeUserRepository,
        tokens: FakeVerificationTokenService,
        hasher: FakePasswordHasher,
    ) -> ResetPasswordHandler:
        return ResetPasswordHandler(
            users=repo,
            tokens=tokens,
            password_hasher=hasher,
            password_policy=PasswordPolicy(),
            reset_policy=RESET_POLICY,
            clock=FakeClock(),
        )

    def _issue_token(self, tokens: FakeVerificationTokenService, user: User, *, issued_at: datetime = NOW) -> str:
        tokens.issue_link(user_id=user.id, issued_at=issued_at)
        return tokens.links[-1].split("token=")[1]

    def test_sets_new_password_and_revokes_sessions(self) -> None:
        repo, tokens, hasher = FakeUserRepository(), FakeVerificationTokenService(), FakePasswordHasher()
        user = repo.seed(_verified_user())
        token = self._issue_token(tokens, user)

        result = self._handler(repo, tokens, hasher).handle(ResetPasswordCommand(token=token, new_password=STRONG_PASSWORD))

        assert hasher.hashed == [STRONG_PASSWORD]
        assert isinstance(result.events[0], PasswordResetCompleted)
        assert repo.saved[-1] is user
        assert user.credentials_invalidated_at == NOW  # cut-off stamped → sessions revoked

    def test_invalid_token_is_rejected(self) -> None:
        repo, tokens, hasher = FakeUserRepository(), FakeVerificationTokenService(), FakePasswordHasher()

        with pytest.raises(InvalidVerificationTokenError):
            self._handler(repo, tokens, hasher).handle(ResetPasswordCommand(token="garbage", new_password=STRONG_PASSWORD))

    def test_token_for_unknown_user_is_rejected_as_invalid(self) -> None:
        # A valid signature for an account that no longer exists must not 404 (that
        # would confirm existence); it surfaces as an invalid token (422).
        repo, tokens, hasher = FakeUserRepository(), FakeVerificationTokenService(), FakePasswordHasher()
        tokens.issue_link(user_id=UserId.generate(), issued_at=NOW)
        token = tokens.links[-1].split("token=")[1]

        with pytest.raises(InvalidVerificationTokenError):
            self._handler(repo, tokens, hasher).handle(ResetPasswordCommand(token=token, new_password=STRONG_PASSWORD))

    def test_expired_link_is_state_conflict(self) -> None:
        repo, tokens, hasher = FakeUserRepository(), FakeVerificationTokenService(), FakePasswordHasher()
        user = repo.seed(_verified_user())
        # Issued more than an hour before the frozen clock's NOW.
        token = self._issue_token(tokens, user, issued_at=NOW - timedelta(hours=2))

        with pytest.raises(UserStateConflictError) as excinfo:
            self._handler(repo, tokens, hasher).handle(ResetPasswordCommand(token=token, new_password=STRONG_PASSWORD))
        assert excinfo.value.domain_code == "VerificationExpiredError"

    def test_weak_password_is_rejected(self) -> None:
        repo, tokens, hasher = FakeUserRepository(), FakeVerificationTokenService(), FakePasswordHasher()
        user = repo.seed(_verified_user())
        token = self._issue_token(tokens, user)

        with pytest.raises(WeakPasswordError):
            self._handler(repo, tokens, hasher).handle(ResetPasswordCommand(token=token, new_password="weak"))
        # A rejected reset leaves the account untouched.
        assert user.credentials_invalidated_at is None
