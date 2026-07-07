"""Integration tests for :class:`JWTService` (the ``TokenService`` adapter).

These exercise the real SimpleJWT token backend **and** its blacklist tables, so
they run against the real database repointed to PostgreSQL by
``tests/infrastructure/conftest.py`` and are marked ``django_db``. They cover the
full lifecycle: issue → validate → rotate (old token blacklisted, cannot be
replayed) → revoke, plus rejection of malformed tokens.
"""

from __future__ import annotations

import pytest
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.identity.application.dto import TokenPairDto
from apps.identity.application.exceptions import InvalidTokenError
from apps.identity.application.interfaces import TokenService
from apps.identity.infrastructure.auth import JWTService

_SUBJECT = "018f9c2a-7e3b-7c21-9a1b-2c4e6f8a0d11"


def test_conforms_to_the_port() -> None:
    assert isinstance(JWTService(), TokenService)


def test_issue_returns_a_usable_pair_carrying_the_subject() -> None:
    pair = JWTService().issue(subject=_SUBJECT)

    assert isinstance(pair, TokenPairDto)
    assert pair.token_type == "Bearer"
    assert pair.expires_in == int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds())
    access = AccessToken(pair.access_token)  # type: ignore[arg-type]
    assert access[jwt_settings.USER_ID_CLAIM] == _SUBJECT


@pytest.mark.django_db
def test_subject_of_extracts_the_identity() -> None:
    # Decoding a valid refresh token verifies blacklist membership, which reads the
    # database — so this needs db access even though nothing is written.
    service = JWTService()
    pair = service.issue(subject=_SUBJECT)

    assert service.subject_of(pair.refresh_token) == _SUBJECT


@pytest.mark.django_db
def test_rotate_issues_a_new_pair_and_blacklists_the_old_token() -> None:
    service = JWTService()
    original = service.issue(subject=_SUBJECT)

    rotated = service.rotate(refresh_token=original.refresh_token)

    assert rotated.refresh_token != original.refresh_token
    rotated_access = AccessToken(rotated.access_token)  # type: ignore[arg-type]
    assert rotated_access[jwt_settings.USER_ID_CLAIM] == _SUBJECT
    # The rotated-away token is now blacklisted and cannot be replayed.
    with pytest.raises(InvalidTokenError):
        service.rotate(refresh_token=original.refresh_token)


@pytest.mark.django_db
def test_revoke_blacklists_the_token() -> None:
    service = JWTService()
    pair = service.issue(subject=_SUBJECT)

    service.revoke(refresh_token=pair.refresh_token)

    with pytest.raises(InvalidTokenError):
        service.rotate(refresh_token=pair.refresh_token)


def test_rotate_rejects_a_malformed_token() -> None:
    with pytest.raises(InvalidTokenError):
        JWTService().rotate(refresh_token="not-a-jwt")


def test_revoke_rejects_a_malformed_token() -> None:
    with pytest.raises(InvalidTokenError):
        JWTService().revoke(refresh_token="not-a-jwt")
