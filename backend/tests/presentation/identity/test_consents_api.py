"""End-to-end REST tests for the consent journal (``/users/me/consents``).

The journal is what makes the published policy's §13.3 checkable — one record per
consent, carrying the version of the text the person actually saw, kept when the
consent is withdrawn. These tests assert exactly those properties, through the real
API against real PostgreSQL, because a journal that quietly loses history would leave
the platform unable to show on what basis it processed anything.
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
CONSENTS_URL = "/api/v1/users/me/consents"

_EMAIL = "guardian@example.com"
_PASSWORD = "Str0ngPass!word"


def _token_from_last_email() -> str:
    body = str(mail.outbox[-1].body)
    match = re.search(r"https?://\S+", body)
    assert match is not None
    return parse_qs(urlparse(match.group(0)).query)["token"][0]


def _register(api: APIClient, **extra: Any) -> Any:
    mail.outbox.clear()
    return api.post(
        REGISTRATION_URL,
        {"email": _EMAIL, "password": _PASSWORD, "firstName": "Irina", "lastName": "Smirnova", **extra},
        format="json",
    )


def _sign_in(api: APIClient) -> None:
    confirmed = api.post(EMAIL_CONFIRM_URL, {"token": _token_from_last_email()}, format="json")
    assert confirmed.status_code == 200, confirmed.data
    login = api.post(SESSIONS_URL, {"email": _EMAIL, "password": _PASSWORD}, format="json")
    assert login.status_code == 201, login.data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")


@pytest.fixture
def client() -> APIClient:
    """An authenticated client for an account that accepted nothing yet."""
    api = APIClient()
    assert _register(api).status_code == 201
    _sign_in(api)
    return api


def _codes(payload: Any) -> dict[str, dict[str, Any]]:
    return {item["consentType"]: item for item in payload["data"]}


class TestRegistrationConsents:
    def test_consents_ticked_on_the_form_are_recorded_with_the_account(self) -> None:
        api = APIClient()
        response = _register(
            api,
            consents=[
                {"consentType": "terms_of_service", "version": "1.0"},
                {"consentType": "privacy_policy", "version": "1.0"},
                {"consentType": "data_processing", "version": "1.0"},
            ],
        )
        assert response.status_code == 201, response.data

        _sign_in(api)
        journal = api.get(CONSENTS_URL)
        assert journal.status_code == 200, journal.data
        recorded = _codes(journal.data)
        # The account and the basis on which its data is processed come into being
        # together; nothing here was a second request that could have failed.
        assert set(recorded) == {"terms_of_service", "privacy_policy", "data_processing"}
        assert recorded["data_processing"]["version"] == "1.0"
        assert recorded["data_processing"]["grantedAt"] is not None

    def test_registration_without_consents_still_succeeds(self) -> None:
        # Native clients and integrations register without a form; the journal is then
        # simply empty rather than the registration being refused.
        api = APIClient()
        assert _register(api).status_code == 201
        _sign_in(api)
        assert api.get(CONSENTS_URL).data["data"] == []


class TestConsentJournal:
    def test_records_a_consent_at_the_version_the_client_displayed(self, client: APIClient) -> None:
        response = client.post(
            CONSENTS_URL,
            {"consentType": "marketing", "version": "1.0", "purpose": "Информационные рассылки"},
            format="json",
        )
        assert response.status_code == 201, response.data
        entry = response.data["data"][0]
        assert entry["consentType"] == "marketing"
        assert entry["version"] == "1.0"
        assert entry["status"] == "active"
        assert entry["purpose"] == "Информационные рассылки"

    def test_re_accepting_supersedes_rather_than_overwrites(self, client: APIClient) -> None:
        assert client.post(CONSENTS_URL, {"consentType": "privacy_policy", "version": "1.0"}, format="json").status_code == 201
        assert client.post(CONSENTS_URL, {"consentType": "privacy_policy", "version": "1.1"}, format="json").status_code == 201

        active = client.get(CONSENTS_URL)
        assert [item["version"] for item in active.data["data"]] == ["1.1"]

        # The earlier wording is still answerable for: which version was in force in
        # March is a question the platform must be able to answer later.
        history = client.get(f"{CONSENTS_URL}?history=true")
        versions = {(item["version"], item["status"]) for item in history.data["data"]}
        assert versions == {("1.1", "active"), ("1.0", "superseded")}

    def test_a_consent_for_one_child_does_not_supersede_another_child(self, client: APIClient) -> None:
        first = "018f9c2a-7e3b-7c21-9a1b-2c4e6f8a0d11"
        second = "018f9c2a-7e3b-7c21-9a1b-2c4e6f8a0d22"
        for participant in (first, second):
            response = client.post(
                CONSENTS_URL,
                {"consentType": "minor_data_processing", "version": "1.0", "subjectParticipantId": participant},
                format="json",
            )
            assert response.status_code == 201, response.data

        active = client.get(CONSENTS_URL)
        subjects = {item["subjectParticipantId"] for item in active.data["data"]}
        assert subjects == {first, second}

    def test_withdrawal_keeps_the_record_and_stamps_it(self, client: APIClient) -> None:
        assert client.post(CONSENTS_URL, {"consentType": "marketing", "version": "1.0"}, format="json").status_code == 201

        withdrawn = client.delete(f"{CONSENTS_URL}/marketing")
        assert withdrawn.status_code == 204

        assert client.get(CONSENTS_URL).data["data"] == []
        history = client.get(f"{CONSENTS_URL}?history=true").data["data"]
        assert len(history) == 1
        assert history[0]["status"] == "withdrawn"
        assert history[0]["withdrawnAt"] is not None

    def test_withdrawing_what_was_never_granted_is_not_an_error(self, client: APIClient) -> None:
        # Art. 5 of Law No. 99-З lets a subject withdraw at any time without giving
        # reasons; answering "you never gave it" only invites them to try again.
        assert client.delete(f"{CONSENTS_URL}/marketing").status_code == 204

    def test_the_journal_is_the_caller_s_own(self) -> None:
        anonymous = APIClient()
        assert anonymous.get(CONSENTS_URL).status_code == 401
        assert anonymous.post(CONSENTS_URL, {"consentType": "marketing", "version": "1.0"}, format="json").status_code == 401

    def test_malformed_request_is_a_problem_document(self, client: APIClient) -> None:
        response = client.post(CONSENTS_URL, {"version": "1.0"}, format="json")
        assert response.status_code == 400
        assert response["Content-Type"].startswith("application/problem+json")
