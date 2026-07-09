"""End-to-end REST tests for the Identity authentication API (API-001 §4).

Driven through DRF's ``APIClient`` against real PostgreSQL — the full edge is
exercised: serializer validation, the command/handler/DTO flow, JWT issuance and
rotation, the SimpleJWT blacklist, the ``data``/``meta`` success envelope
(API-000 §7), and RFC 9457 ``application/problem+json`` errors (API-000 §8). No
layer is mocked.
"""

from __future__ import annotations

import re
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTRATION_URL = "/api/v1/auth/registration"
SESSIONS_URL = "/api/v1/auth/sessions"
CURRENT_SESSION_URL = "/api/v1/auth/sessions/current"
REFRESH_URL = "/api/v1/auth/token/refresh"
EMAIL_CONFIRM_URL = "/api/v1/auth/email-verification/confirmations"
EMAIL_REQUEST_URL = "/api/v1/auth/email-verification/requests"

_PASSWORD = "Str0ngPass!word"
_PROBLEM_CT = "application/problem+json"


def _registration_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": "parent@example.com",
        "password": _PASSWORD,
        "firstName": "Irina",
        "lastName": "Smirnova",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def _register(client: APIClient, **overrides: object) -> None:
    response = client.post(REGISTRATION_URL, _registration_payload(**overrides), format="json")
    assert response.status_code == 201, response.data


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_creates_account_and_returns_the_envelope(self, client: APIClient) -> None:
        response = client.post(REGISTRATION_URL, _registration_payload(), format="json")

        assert response.status_code == 201
        assert response["Location"].startswith("/api/v1/users/")
        data = response.data["data"]
        assert data["type"] == "user"
        assert data["email"] == "parent@example.com"
        assert data["displayName"] == "Irina Smirnova"
        assert data["status"] == "registered"
        assert data["emailVerified"] is False
        assert data["mfaEnabled"] is False
        assert "requestId" in response.data["meta"]

    def test_duplicate_email_is_a_conflict(self, client: APIClient) -> None:
        _register(client)

        response = client.post(REGISTRATION_URL, _registration_payload(), format="json")

        assert response.status_code == 409
        assert response["Content-Type"] == _PROBLEM_CT
        assert response.data["code"] == "IDN-003"
        assert response.data["type"].endswith("/conflict")

    def test_weak_password_is_unprocessable(self, client: APIClient) -> None:
        response = client.post(REGISTRATION_URL, _registration_payload(password="weak"), format="json")

        assert response.status_code == 422
        assert response["Content-Type"] == _PROBLEM_CT
        assert response.data["type"].endswith("/validation-error")
        pointers = {err["pointer"] for err in response.data["errors"]}
        assert "/password" in pointers

    def test_missing_field_is_a_bad_request(self, client: APIClient) -> None:
        payload = _registration_payload()
        del payload["password"]

        response = client.post(REGISTRATION_URL, payload, format="json")

        assert response.status_code == 400
        assert response["Content-Type"] == _PROBLEM_CT
        assert any(err["pointer"] == "/password" for err in response.data["errors"])


# ---------------------------------------------------------------------------
# Login (session creation)
# ---------------------------------------------------------------------------


class TestLogin:
    def test_issues_tokens_and_sets_the_refresh_cookie(self, client: APIClient) -> None:
        _register(client)

        response = client.post(SESSIONS_URL, {"email": "parent@example.com", "password": _PASSWORD}, format="json")

        assert response.status_code == 201
        data = response.data["data"]
        assert data["type"] == "session"
        assert data["accessToken"]
        assert data["tokenType"] == "Bearer"
        assert data["expiresIn"] == 900
        assert data["user"]["displayName"] == "Irina Smirnova"
        cookie = response.cookies["refresh_token"]
        assert cookie.value
        assert cookie["httponly"]

    def test_wrong_password_is_unauthorized(self, client: APIClient) -> None:
        _register(client)

        response = client.post(SESSIONS_URL, {"email": "parent@example.com", "password": "nope"}, format="json")

        assert response.status_code == 401
        assert response["Content-Type"] == _PROBLEM_CT
        assert response.data["type"].endswith("/authentication-failed")

    def test_unknown_email_is_unauthorized(self, client: APIClient) -> None:
        response = client.post(SESSIONS_URL, {"email": "ghost@example.com", "password": _PASSWORD}, format="json")

        assert response.status_code == 401
        assert response.data["type"].endswith("/authentication-failed")


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


class TestTokenRefresh:
    def _login(self, client: APIClient) -> dict[str, Any]:
        _register(client)
        response = client.post(SESSIONS_URL, {"email": "parent@example.com", "password": _PASSWORD}, format="json")
        return cast(dict[str, Any], response.data["data"])

    def test_rotates_the_refresh_cookie(self, client: APIClient) -> None:
        self._login(client)  # refresh cookie now stored on the client

        response = client.post(REFRESH_URL, {}, format="json")

        assert response.status_code == 200
        assert response.data["data"]["accessToken"]
        assert response.cookies["refresh_token"].value

    def test_reused_refresh_token_is_rejected(self, client: APIClient) -> None:
        session = self._login(client)
        original_refresh = session["refreshToken"]
        # Rotate once using the explicit token (native-client flow).
        first = client.post(REFRESH_URL, {"refreshToken": original_refresh}, format="json")
        assert first.status_code == 200

        replay = client.post(REFRESH_URL, {"refreshToken": original_refresh}, format="json")

        assert replay.status_code == 401
        assert replay["Content-Type"] == _PROBLEM_CT

    def test_missing_refresh_token_is_unauthorized(self, client: APIClient) -> None:
        response = client.post(REFRESH_URL, {}, format="json")

        assert response.status_code == 401
        assert response.data["type"].endswith("/unauthorized")


# ---------------------------------------------------------------------------
# Logout (current-session deletion)
# ---------------------------------------------------------------------------


class TestLogout:
    def test_revokes_the_session_and_clears_the_cookie(self, client: APIClient) -> None:
        _register(client)
        login = client.post(SESSIONS_URL, {"email": "parent@example.com", "password": _PASSWORD}, format="json")
        access = login.data["data"]["accessToken"]
        refresh = login.data["data"]["refreshToken"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.delete(CURRENT_SESSION_URL)

        assert response.status_code == 204
        # The revoked refresh token can no longer be rotated.
        client.credentials()
        replay = client.post(REFRESH_URL, {"refreshToken": refresh}, format="json")
        assert replay.status_code == 401

    def test_requires_authentication(self, client: APIClient) -> None:
        response = client.delete(CURRENT_SESSION_URL)

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


def _token_from_last_email() -> str:
    """Extract the ``token`` query parameter from the most recent sent email."""
    assert len(mail.outbox) >= 1
    body = str(mail.outbox[-1].body)
    match = re.search(r"https?://\S+", body)
    assert match is not None
    return parse_qs(urlparse(match.group(0)).query)["token"][0]


class TestEmailVerification:
    def test_registration_sends_exactly_one_verification_email(self, client: APIClient) -> None:
        mail.outbox.clear()

        _register(client)

        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == ["parent@example.com"]
        assert message.from_email
        assert message.subject
        assert "verify-email?token=" in message.body

    def test_confirming_the_link_verifies_the_account(self, client: APIClient) -> None:
        mail.outbox.clear()
        _register(client)
        token = _token_from_last_email()

        response = client.post(EMAIL_CONFIRM_URL, {"token": token}, format="json")

        assert response.status_code == 200
        data = response.data["data"]
        assert data["emailVerified"] is True
        assert data["status"] == "active"

    def test_verified_account_can_log_in(self, client: APIClient) -> None:
        mail.outbox.clear()
        _register(client)
        client.post(EMAIL_CONFIRM_URL, {"token": _token_from_last_email()}, format="json")

        login = client.post(SESSIONS_URL, {"email": "parent@example.com", "password": _PASSWORD}, format="json")

        assert login.status_code == 201
        assert login.data["data"]["user"]["emailVerified"] is True

    def test_garbage_token_is_unprocessable(self, client: APIClient) -> None:
        response = client.post(EMAIL_CONFIRM_URL, {"token": "not-a-token"}, format="json")

        assert response.status_code == 422
        assert response["Content-Type"] == _PROBLEM_CT
        assert response.data["type"].endswith("/validation-error")

    def test_confirming_twice_is_a_conflict(self, client: APIClient) -> None:
        mail.outbox.clear()
        _register(client)
        token = _token_from_last_email()
        first = client.post(EMAIL_CONFIRM_URL, {"token": token}, format="json")
        assert first.status_code == 200

        second = client.post(EMAIL_CONFIRM_URL, {"token": token}, format="json")

        assert second.status_code == 409
        assert second["Content-Type"] == _PROBLEM_CT
        assert second.data["type"].endswith("/conflict")

    def test_new_account_is_unverified_then_first_confirm_200_second_409(self, client: APIClient) -> None:
        # Regression: a brand-new account must NOT be pre-verified. The FIRST
        # confirmation of its emailed token verifies it (200); only a SECOND
        # confirmation is a conflict (409). A first-attempt 409 would mean the
        # aggregate was wrongly treated as already verified at registration.
        mail.outbox.clear()
        registration = client.post(REGISTRATION_URL, _registration_payload(), format="json")
        assert registration.status_code == 201
        assert registration.data["data"]["emailVerified"] is False
        assert registration.data["data"]["status"] == "registered"

        token = _token_from_last_email()

        first = client.post(EMAIL_CONFIRM_URL, {"token": token}, format="json")
        assert first.status_code == 200
        assert first.data["data"]["emailVerified"] is True

        second = client.post(EMAIL_CONFIRM_URL, {"token": token}, format="json")
        assert second.status_code == 409
        assert second["Content-Type"] == _PROBLEM_CT
        assert second.data["type"].endswith("/conflict")

    def test_resend_requires_authentication(self, client: APIClient) -> None:
        response = client.post(EMAIL_REQUEST_URL)

        assert response.status_code == 401

    def test_resend_dispatches_a_new_email(self, client: APIClient) -> None:
        _register(client)
        login = client.post(SESSIONS_URL, {"email": "parent@example.com", "password": _PASSWORD}, format="json")
        access = login.data["data"]["accessToken"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        mail.outbox.clear()

        response = client.post(EMAIL_REQUEST_URL)

        assert response.status_code == 202
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["parent@example.com"]
