"""Unit tests for the signed email-verification token adapter.

Exercises :class:`SignedVerificationTokenService` against Django's real signing
(no mocks): a minted link round-trips back to its payload, and a tampered or
malformed token is rejected with :class:`InvalidVerificationTokenError`. These
need Django settings (``SECRET_KEY``, ``FRONTEND_BASE_URL``) but no database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest

from apps.identity.application.exceptions import InvalidVerificationTokenError
from apps.identity.domain.value_objects import UserId
from apps.identity.infrastructure.messaging import SignedVerificationTokenService

NOW = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)


def _token_from_link(link: str) -> str:
    return parse_qs(urlparse(link).query)["token"][0]


class TestSignedVerificationTokenService:
    def test_issued_link_round_trips_to_payload(self) -> None:
        service = SignedVerificationTokenService(base_url="https://frontend.test")
        user_id = UserId.generate()

        link = service.issue_link(user_id=user_id, issued_at=NOW)

        assert link.startswith("https://frontend.test/verify-email?token=")
        decoded = service.verify(_token_from_link(link))
        assert decoded.user_id == user_id
        assert decoded.issued_at == NOW

    def test_base_url_trailing_slash_is_normalized(self) -> None:
        service = SignedVerificationTokenService(base_url="https://frontend.test/")

        link = service.issue_link(user_id=UserId.generate(), issued_at=NOW)

        assert "https://frontend.test/verify-email?token=" in link

    def test_tampered_token_is_rejected(self) -> None:
        service = SignedVerificationTokenService(base_url="https://frontend.test")
        token = _token_from_link(service.issue_link(user_id=UserId.generate(), issued_at=NOW))

        with pytest.raises(InvalidVerificationTokenError):
            service.verify(token + "tampered")

    def test_garbage_token_is_rejected(self) -> None:
        service = SignedVerificationTokenService(base_url="https://frontend.test")

        with pytest.raises(InvalidVerificationTokenError):
            service.verify("not-a-real-token")
