"""Unit tests for the session use cases (refresh / logout).

Framework-free: the handlers are exercised against the in-memory
:class:`FakeTokenService`, asserting they are faithful pass-throughs to the
``TokenService`` port and that an unusable token surfaces as
:class:`InvalidTokenError` (mapped to ``401`` at the edge). No database, no JWTs.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from apps.identity.application.commands import LogoutCommand, RefreshTokenCommand
from apps.identity.application.dto import TokenPairDto
from apps.identity.application.exceptions import InvalidTokenError
from apps.identity.application.handlers import LogoutHandler, RefreshTokenHandler
from apps.identity.domain.policies import PasswordResetPolicy
from apps.identity.domain.value_objects import Email, FullName, PasswordHash, UserId

from .fakes import NOW, FakeTokenService, FakeUserRepository

_SUBJECT = UserId.generate()


def _register(user_id: UserId):  # type: ignore[no-untyped-def]
    from apps.identity.domain.entities import User

    return User.register(
        user_id=user_id,
        email=Email("recover@example.com"),
        full_name=FullName.of("Reset", "Test"),
        password_hash=PasswordHash.from_hash("$argon2id$v=19$m=1,t=1,p=1$c2FsdA$old"),
        now=NOW,
    )


class TestRefreshTokenHandler:
    def test_rotates_and_returns_a_fresh_pair(self) -> None:
        tokens = FakeTokenService()
        original = tokens.issue(subject=_SUBJECT.json())
        handler = RefreshTokenHandler(tokens=tokens, users=FakeUserRepository())

        result = handler.handle(RefreshTokenCommand(refresh_token=original.refresh_token))

        assert isinstance(result, TokenPairDto)
        assert result.refresh_token != original.refresh_token
        assert result.token_type == "Bearer"
        assert tokens.rotated == [original.refresh_token]

    def test_rejected_token_raises_invalid_token(self) -> None:
        handler = RefreshTokenHandler(tokens=FakeTokenService(), users=FakeUserRepository())

        with pytest.raises(InvalidTokenError):
            handler.handle(RefreshTokenCommand(refresh_token="not-a-real-token"))

    def test_a_rotated_token_cannot_be_replayed(self) -> None:
        tokens = FakeTokenService()
        original = tokens.issue(subject=_SUBJECT.json())
        handler = RefreshTokenHandler(tokens=tokens, users=FakeUserRepository())
        handler.handle(RefreshTokenCommand(refresh_token=original.refresh_token))

        with pytest.raises(InvalidTokenError):
            handler.handle(RefreshTokenCommand(refresh_token=original.refresh_token))

    def test_token_issued_before_credential_cutoff_is_rejected(self) -> None:
        # A token minted at NOW, but the account's credentials were invalidated
        # afterwards (a completed password reset) — the session must be refused.
        tokens = FakeTokenService(issued_at=NOW)
        original = tokens.issue(subject=_SUBJECT.json())
        users = FakeUserRepository()
        user, _ = _register(_SUBJECT)
        user.reset_password(
            PasswordHash.from_hash("$argon2id$v=19$m=1,t=1,p=1$c2FsdA$new"),
            policy=PasswordResetPolicy(),
            issued_at=NOW,
            now=NOW + timedelta(minutes=1),
        )
        users.seed(user)
        handler = RefreshTokenHandler(tokens=tokens, users=users)

        with pytest.raises(InvalidTokenError):
            handler.handle(RefreshTokenCommand(refresh_token=original.refresh_token))
        assert tokens.rotated == []


class TestLogoutHandler:
    def test_revokes_the_refresh_token(self) -> None:
        tokens = FakeTokenService()
        issued = tokens.issue(subject="018f-user")
        handler = LogoutHandler(tokens=tokens)

        handler.handle(LogoutCommand(refresh_token=issued.refresh_token))

        assert tokens.revoked == [issued.refresh_token]

    def test_unusable_token_raises_invalid_token(self) -> None:
        handler = LogoutHandler(tokens=FakeTokenService())

        with pytest.raises(InvalidTokenError):
            handler.handle(LogoutCommand(refresh_token="already-gone"))
