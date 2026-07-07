"""Unit tests for the session use cases (refresh / logout).

Framework-free: the handlers are exercised against the in-memory
:class:`FakeTokenService`, asserting they are faithful pass-throughs to the
``TokenService`` port and that an unusable token surfaces as
:class:`InvalidTokenError` (mapped to ``401`` at the edge). No database, no JWTs.
"""

from __future__ import annotations

import pytest

from apps.identity.application.commands import LogoutCommand, RefreshTokenCommand
from apps.identity.application.dto import TokenPairDto
from apps.identity.application.exceptions import InvalidTokenError
from apps.identity.application.handlers import LogoutHandler, RefreshTokenHandler

from .fakes import FakeTokenService


class TestRefreshTokenHandler:
    def test_rotates_and_returns_a_fresh_pair(self) -> None:
        tokens = FakeTokenService()
        original = tokens.issue(subject="018f-user")
        handler = RefreshTokenHandler(tokens=tokens)

        result = handler.handle(RefreshTokenCommand(refresh_token=original.refresh_token))

        assert isinstance(result, TokenPairDto)
        assert result.refresh_token != original.refresh_token
        assert result.token_type == "Bearer"
        assert tokens.rotated == [original.refresh_token]

    def test_rejected_token_raises_invalid_token(self) -> None:
        handler = RefreshTokenHandler(tokens=FakeTokenService())

        with pytest.raises(InvalidTokenError):
            handler.handle(RefreshTokenCommand(refresh_token="not-a-real-token"))

    def test_a_rotated_token_cannot_be_replayed(self) -> None:
        tokens = FakeTokenService()
        original = tokens.issue(subject="018f-user")
        handler = RefreshTokenHandler(tokens=tokens)
        handler.handle(RefreshTokenCommand(refresh_token=original.refresh_token))

        with pytest.raises(InvalidTokenError):
            handler.handle(RefreshTokenCommand(refresh_token=original.refresh_token))


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
