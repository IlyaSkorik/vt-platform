"""Unit tests for the signed password-reset token adapter.

Exercises :class:`SignedPasswordResetTokenService` against Django's real signing
(no mocks): a minted link round-trips back to its payload, a tampered/malformed
token is rejected, and — critically — a token minted by the **email-verification**
service is rejected here (and vice versa), proving the two are salt-isolated so a
verification token can never be replayed as a reset token. Needs Django settings
(``SECRET_KEY``, ``FRONTEND_BASE_URL``) but no database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest

from apps.identity.application.exceptions import InvalidVerificationTokenError
from apps.identity.domain.value_objects import UserId
from apps.identity.infrastructure.messaging import (
    SignedPasswordResetTokenService,
    SignedVerificationTokenService,
)

NOW = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)


def _token_from_link(link: str) -> str:
    return parse_qs(urlparse(link).query)["token"][0]


class TestSignedPasswordResetTokenService:
    def test_issued_link_round_trips_to_payload(self) -> None:
        service = SignedPasswordResetTokenService(base_url="https://frontend.test")
        user_id = UserId.generate()

        link = service.issue_link(user_id=user_id, issued_at=NOW)

        assert link.startswith("https://frontend.test/reset-password?token=")
        decoded = service.verify(_token_from_link(link))
        assert decoded.user_id == user_id
        assert decoded.issued_at == NOW

    def test_base_url_trailing_slash_is_normalized(self) -> None:
        service = SignedPasswordResetTokenService(base_url="https://frontend.test/")

        link = service.issue_link(user_id=UserId.generate(), issued_at=NOW)

        assert "https://frontend.test/reset-password?token=" in link

    def test_tampered_token_is_rejected(self) -> None:
        service = SignedPasswordResetTokenService(base_url="https://frontend.test")
        token = _token_from_link(service.issue_link(user_id=UserId.generate(), issued_at=NOW))

        with pytest.raises(InvalidVerificationTokenError):
            service.verify(token + "tampered")

    def test_garbage_token_is_rejected(self) -> None:
        service = SignedPasswordResetTokenService(base_url="https://frontend.test")

        with pytest.raises(InvalidVerificationTokenError):
            service.verify("not-a-real-token")

    def test_verification_token_cannot_be_replayed_as_reset(self) -> None:
        # A token minted for email verification must not verify as a reset token:
        # the salts differ, so the signature check fails.
        verification = SignedVerificationTokenService(base_url="https://frontend.test")
        reset = SignedPasswordResetTokenService(base_url="https://frontend.test")
        verify_token = _token_from_link(verification.issue_link(user_id=UserId.generate(), issued_at=NOW))

        with pytest.raises(InvalidVerificationTokenError):
            reset.verify(verify_token)

    def test_reset_token_cannot_be_replayed_as_verification(self) -> None:
        verification = SignedVerificationTokenService(base_url="https://frontend.test")
        reset = SignedPasswordResetTokenService(base_url="https://frontend.test")
        reset_token = _token_from_link(reset.issue_link(user_id=UserId.generate(), issued_at=NOW))

        with pytest.raises(InvalidVerificationTokenError):
            verification.verify(reset_token)
