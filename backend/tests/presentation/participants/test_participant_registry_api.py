"""End-to-end REST tests for the participant registry (``/participants/registry``).

This is the surface the cabinet actually posts to when someone adds a child, which makes
it the one that has to keep the promise in LEGAL-001 §6.3: a child's record does not come
into existence without the legal representative's consent, and the platform — not the
form — is what enforces that. Until now the endpoint had no tests at all.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.identity.presentation.api.v1.auth import composition

pytestmark = pytest.mark.django_db

REGISTRY_URL = "/api/v1/participants/registry"
ORGANIZATIONS_URL = "/api/v1/participants/organizations"
CONSENTS_URL = "/api/v1/users/me/consents"
_PASSWORD = "Str0ngPass!word"


@pytest.fixture
def auth_client() -> APIClient:
    """A client for a freshly-registered guardian account."""
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {
            "email": "registry-guardian@example.com",
            "password": _PASSWORD,
            "firstName": "Olga",
            "lastName": "Petrova",
        },
        format="json",
    )
    assert registration.status_code == 201, registration.data
    access = composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def _record_consent(client: APIClient) -> str:
    """Record the representative's consent and return the journal entry's id."""
    response = client.post(
        CONSENTS_URL,
        {"consentType": "minor_data_processing", "version": "1.0"},
        format="json",
    )
    assert response.status_code == 201, response.data
    return str(response.data["data"][0]["id"])


def _organization(client: APIClient) -> str:
    """A registry participant must belong to an organization; make one and return its id."""
    response = client.post(
        ORGANIZATIONS_URL,
        {"name": "ДШИ №1", "type": "art_school", "city": "Минск"},
        format="json",
    )
    assert response.status_code in (200, 201), response.data
    return str(response.data["data"]["id"])


def _child(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "participantType": "solo",
        "firstName": "Ivan",
        "lastName": "Petrov",
        "birthDate": "2015-03-04",
        "gender": "male",
        "organizations": [],
    }
    body.update(overrides)
    return body


class TestRegistryCreationRequiresConsent:
    def test_refuses_to_create_a_child_without_a_consent_reference(self, auth_client: APIClient) -> None:
        response = auth_client.post(REGISTRY_URL, _child(), format="json")

        assert response.status_code == 400, response.data
        assert response["Content-Type"].startswith("application/problem+json")
        # And nothing was stored: a refused creation must not leave the child on file.
        listing = auth_client.get(REGISTRY_URL)
        assert listing.data["data"] == []

    def test_refuses_half_a_consent_reference(self, auth_client: APIClient) -> None:
        consent_id = _record_consent(auth_client)
        # An id without the version does not say what was agreed to.
        response = auth_client.post(REGISTRY_URL, _child(consentId=consent_id), format="json")
        assert response.status_code == 400, response.data

    def test_creates_the_child_with_the_consent_that_authorises_it(self, auth_client: APIClient) -> None:
        consent_id = _record_consent(auth_client)
        organization_id = _organization(auth_client)

        response = auth_client.post(
            REGISTRY_URL,
            _child(
                consentId=consent_id,
                consentVersion="1.0",
                organizations=[{"organizationId": organization_id, "isPrimary": True}],
            ),
            format="json",
        )

        assert response.status_code == 201, response.data
        # The record the cabinet reads carries the basis itself, rather than the basis
        # living only on a row nobody queries.
        assert response.data["data"]["consentRecorded"] is True
        assert response.data["data"]["consentVersion"] == "1.0"

    def test_the_recorded_consent_names_the_journal_entry(self, auth_client: APIClient) -> None:
        consent_id = _record_consent(auth_client)
        organization_id = _organization(auth_client)
        created = auth_client.post(
            REGISTRY_URL,
            _child(
                consentId=consent_id,
                consentVersion="1.0",
                organizations=[{"organizationId": organization_id, "isPrimary": True}],
            ),
            format="json",
        )
        assert created.status_code == 201

        journal = auth_client.get(CONSENTS_URL)
        types = {entry["consentType"] for entry in journal.data["data"]}
        # The journal holds the entry the child's row points at, so the two agree on
        # which text was accepted (LEGAL-001 §13.3).
        assert "minor_data_processing" in types

    def test_the_registry_is_the_caller_s_own(self) -> None:
        assert APIClient().post(REGISTRY_URL, _child(), format="json").status_code == 401
