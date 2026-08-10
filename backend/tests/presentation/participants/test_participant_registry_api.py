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


def _record_consent(client: APIClient, consent_type: str = "minor_data_processing") -> str:
    """Record a consent of that type and return the journal entry's id."""
    response = client.post(
        CONSENTS_URL,
        {"consentType": consent_type, "version": "1.0"},
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


def _adult(**overrides: Any) -> dict[str, Any]:
    """The same body for someone who is plainly over eighteen today."""
    return _child(firstName="Anna", lastName="Sidorova", birthDate="1994-06-20", gender="female", **overrides)


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

    def test_refuses_a_consent_belonging_to_another_account(self, auth_client: APIClient) -> None:
        # A second account's genuine consent is still not this caller's basis for holding
        # a child's data.
        other = APIClient()
        registration = other.post(
            "/api/v1/auth/registration",
            {
                "email": "someone-else@example.com",
                "password": _PASSWORD,
                "firstName": "Anna",
                "lastName": "Ivanova",
            },
            format="json",
        )
        assert registration.status_code == 201
        access = composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
        other.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        foreign_consent = _record_consent(other)
        organization_id = _organization(auth_client)

        response = auth_client.post(
            REGISTRY_URL,
            _child(
                consentId=foreign_consent,
                consentVersion="1.0",
                organizations=[{"organizationId": organization_id, "isPrimary": True}],
            ),
            format="json",
        )

        assert response.status_code == 400, response.data

    def test_refuses_a_withdrawn_consent(self, auth_client: APIClient) -> None:
        consent_id = _record_consent(auth_client)
        assert auth_client.delete("/api/v1/users/me/consents/minor_data_processing").status_code == 204
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

        assert response.status_code == 400, response.data

    def test_the_registry_is_the_caller_s_own(self) -> None:
        assert APIClient().post(REGISTRY_URL, _child(), format="json").status_code == 401


class TestTheBasisFollowsTheParticipantsAge:
    """Which consent authorises the record is decided by the age, server-side.

    Nobody is the legal representative of an adult, so holding an adult participant on a
    ``minor_data_processing`` consent means holding them on a statement that was never
    true (LEGAL-001 §6.2). The endpoint derives the required type from the submitted
    birth date, which is also what stops a caller choosing the weaker basis themselves.
    """

    def test_refuses_an_adult_held_on_a_representatives_consent(self, auth_client: APIClient) -> None:
        consent_id = _record_consent(auth_client, "minor_data_processing")
        organization_id = _organization(auth_client)

        response = auth_client.post(
            REGISTRY_URL,
            _adult(
                consentId=consent_id,
                consentVersion="1.0",
                organizations=[{"organizationId": organization_id, "isPrimary": True}],
            ),
            format="json",
        )

        assert response.status_code == 400, response.data
        assert auth_client.get(REGISTRY_URL).data["data"] == []

    def test_creates_an_adult_on_their_own_confirmed_consent(self, auth_client: APIClient) -> None:
        consent_id = _record_consent(auth_client, "third_party_data_processing")
        organization_id = _organization(auth_client)

        response = auth_client.post(
            REGISTRY_URL,
            _adult(
                consentId=consent_id,
                consentVersion="1.0",
                organizations=[{"organizationId": organization_id, "isPrimary": True}],
            ),
            format="json",
        )

        assert response.status_code == 201, response.data
        assert response.data["data"]["consentRecorded"] is True

    def test_refuses_a_child_held_on_the_adult_basis(self, auth_client: APIClient) -> None:
        # The mirror image, and the one that matters more: a child's record must not rest
        # on "the participant consented themselves".
        consent_id = _record_consent(auth_client, "third_party_data_processing")
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

        assert response.status_code == 400, response.data

    def test_a_collective_keeps_the_representatives_consent(self, auth_client: APIClient) -> None:
        # A collective's row is not a person: its stated date says nothing about whether
        # its members are children, so the stricter basis stands.
        consent_id = _record_consent(auth_client, "minor_data_processing")
        organization_id = _organization(auth_client)

        response = auth_client.post(
            REGISTRY_URL,
            {
                "participantType": "collective",
                "collectiveName": "Ансамбль «Ручеёк»",
                "consentId": consent_id,
                "consentVersion": "1.0",
                "organizations": [{"organizationId": organization_id, "isPrimary": True}],
            },
            format="json",
        )

        assert response.status_code == 201, response.data
