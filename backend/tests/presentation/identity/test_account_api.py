"""End-to-end REST tests for the account self-service API (``/users/me/*``).

Driven through DRF's ``APIClient`` against real PostgreSQL, like the
authentication tests beside them: nothing is mocked, so what these assert is what
the settings screen in the cabinet actually gets back.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTRATION_URL = "/api/v1/auth/registration"
SESSIONS_URL = "/api/v1/auth/sessions"
EMAIL_CONFIRM_URL = "/api/v1/auth/email-verification/confirmations"
ME_URL = "/api/v1/users/me"
PASSWORD_URL = "/api/v1/users/me/password"
EMAIL_URL = "/api/v1/users/me/email"
PHONE_URL = "/api/v1/users/me/phone"

_EMAIL = "holder@example.com"
_PASSWORD = "Str0ngPass!word"
_NEW_PASSWORD = "An0ther$trongOne"
_PROBLEM_CT = "application/problem+json"


def _token_from_last_email() -> str:
    body = str(mail.outbox[-1].body)
    match = re.search(r"https?://\S+", body)
    assert match is not None
    return parse_qs(urlparse(match.group(0)).query)["token"][0]


@pytest.fixture
def client() -> APIClient:
    """An authenticated client for a verified account with a known password."""
    api = APIClient()
    mail.outbox.clear()
    registration = api.post(
        REGISTRATION_URL,
        {"email": _EMAIL, "password": _PASSWORD, "firstName": "Irina", "lastName": "Smirnova"},
        format="json",
    )
    assert registration.status_code == 201, registration.data
    confirmed = api.post(EMAIL_CONFIRM_URL, {"token": _token_from_last_email()}, format="json")
    assert confirmed.status_code == 200, confirmed.data
    login = api.post(SESSIONS_URL, {"email": _EMAIL, "password": _PASSWORD}, format="json")
    assert login.status_code == 201, login.data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
    return api


def _me(client: APIClient) -> dict[str, Any]:
    response = client.get(ME_URL)
    assert response.status_code == 200, response.data
    return dict(response.data["data"]["user"])


class TestChangePassword:
    def test_the_holder_can_replace_their_own_password(self, client: APIClient) -> None:
        response = client.put(
            PASSWORD_URL,
            {"currentPassword": _PASSWORD, "newPassword": _NEW_PASSWORD},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["data"]["email"] == _EMAIL
        fresh = APIClient()
        assert fresh.post(SESSIONS_URL, {"email": _EMAIL, "password": _NEW_PASSWORD}, format="json").status_code == 201
        assert fresh.post(SESSIONS_URL, {"email": _EMAIL, "password": _PASSWORD}, format="json").status_code == 401

    def test_the_session_survives_the_change(self, client: APIClient) -> None:
        """Unlike an emailed reset: the holder is here, and is not signed out mid-task."""
        client.put(PASSWORD_URL, {"currentPassword": _PASSWORD, "newPassword": _NEW_PASSWORD}, format="json")

        assert client.get(ME_URL).status_code == 200

    def test_a_wrong_current_password_is_unauthorized(self, client: APIClient) -> None:
        response = client.put(
            PASSWORD_URL,
            {"currentPassword": "not-the-one", "newPassword": _NEW_PASSWORD},
            format="json",
        )

        assert response.status_code == 401
        assert response["Content-Type"] == _PROBLEM_CT
        fresh = APIClient()
        assert fresh.post(SESSIONS_URL, {"email": _EMAIL, "password": _PASSWORD}, format="json").status_code == 201

    def test_a_weak_new_password_is_unprocessable(self, client: APIClient) -> None:
        response = client.put(PASSWORD_URL, {"currentPassword": _PASSWORD, "newPassword": "weak"}, format="json")

        assert response.status_code == 422
        assert response["Content-Type"] == _PROBLEM_CT

    def test_requires_a_session(self) -> None:
        response = APIClient().put(
            PASSWORD_URL,
            {"currentPassword": _PASSWORD, "newPassword": _NEW_PASSWORD},
            format="json",
        )

        assert response.status_code == 401


class TestChangeEmail:
    def test_moving_the_address_unverifies_it_and_sends_a_fresh_link(self, client: APIClient) -> None:
        mail.outbox.clear()

        response = client.put(
            EMAIL_URL,
            {"email": "moved@example.com", "currentPassword": _PASSWORD},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["data"]["email"] == "moved@example.com"
        assert response.data["data"]["emailVerified"] is False
        assert len(mail.outbox) == 1
        assert mail.outbox[-1].to == ["moved@example.com"]

    def test_the_new_address_can_be_confirmed_and_signed_in_with(self, client: APIClient) -> None:
        mail.outbox.clear()
        client.put(EMAIL_URL, {"email": "moved@example.com", "currentPassword": _PASSWORD}, format="json")

        confirmed = APIClient().post(EMAIL_CONFIRM_URL, {"token": _token_from_last_email()}, format="json")

        assert confirmed.status_code == 200, confirmed.data
        fresh = APIClient()
        assert fresh.post(SESSIONS_URL, {"email": "moved@example.com", "password": _PASSWORD}, format="json").status_code == 201

    def test_a_wrong_current_password_is_unauthorized(self, client: APIClient) -> None:
        response = client.put(EMAIL_URL, {"email": "moved@example.com", "currentPassword": "nope"}, format="json")

        assert response.status_code == 401
        assert _me(client)["email"] == _EMAIL

    def test_an_address_that_belongs_to_someone_else_is_a_conflict(self, client: APIClient) -> None:
        other = APIClient()
        other.post(
            REGISTRATION_URL,
            {"email": "taken@example.com", "password": _PASSWORD, "firstName": "Oleg", "lastName": "Popov"},
            format="json",
        )

        response = client.put(EMAIL_URL, {"email": "taken@example.com", "currentPassword": _PASSWORD}, format="json")

        assert response.status_code == 409
        assert response["Content-Type"] == _PROBLEM_CT

    def test_a_malformed_address_is_a_bad_request(self, client: APIClient) -> None:
        response = client.put(EMAIL_URL, {"email": "not-an-email", "currentPassword": _PASSWORD}, format="json")

        assert response.status_code == 400


class TestChangePhone:
    def test_sets_the_number_and_reports_it_back(self, client: APIClient) -> None:
        response = client.put(PHONE_URL, {"phone": "+79991234567"}, format="json")

        assert response.status_code == 200, response.data
        assert response.data["data"]["phone"] == "+79991234567"
        assert response.data["data"]["phoneVerified"] is False
        # And the composed account reads back the same number the settings screen set.
        assert _me(client)["phone"] == "+79991234567"

    def test_a_malformed_number_is_refused(self, client: APIClient) -> None:
        response = client.put(PHONE_URL, {"phone": "12"}, format="json")

        assert response.status_code in (400, 422)
        assert response["Content-Type"] == _PROBLEM_CT

    def test_requires_a_session(self) -> None:
        assert APIClient().put(PHONE_URL, {"phone": "+79991234567"}, format="json").status_code == 401
