"""Integration tests for the Application (order) REST API v1.

Driven through DRF's ``APIClient`` against real PostgreSQL - the full edge end to
end (serializer -> command -> handler -> repository/ACL -> response), authenticated
with a real JWT from the Identity login endpoint. A competition open for
applications is seeded directly so the create path's Competition ACL check passes.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.base import uuid7
from apps.identity.presentation.api.v1.auth import composition as identity_composition

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _seed_open_competition() -> str:
    """Seed a competition with at least one nomination open for registration; return its id string."""
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel

    competition = CompetitionModel.objects.create(
        organizer_id=uuid7(),
        status="PUBLISHED",
        title="Spring Festival",
        season="2025/2026",
    )
    # Registration is scheduled per nomination, so an open nomination window is what
    # actually admits applications (there is no competition-wide application deadline).
    CategoryModel.objects.create(
        competition=competition,
        name="Vocal",
        registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
        registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
    )
    return str(competition.id)


def _auth(client: APIClient, *, email: str) -> APIClient:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Olga", "lastName": "Petrova"},
        format="json",
    )
    # Mint the session token directly: the login gate refuses unverified accounts,
    # and this BC test only needs an authenticated caller, not the verify flow.
    access = identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def auth_client() -> APIClient:
    return _auth(APIClient(), email="applicant@example.com")


def _create(client: APIClient, competition_id: str) -> Any:
    return client.post("/api/v1/applications", {"competitionId": competition_id}, format="json")


def test_requires_authentication() -> None:
    assert APIClient().get("/api/v1/applications").status_code == 401


def test_create_returns_resource_envelope(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    response = _create(auth_client, competition_id)
    assert response.status_code == 201, response.data
    data = response.data["data"]
    assert data["type"] == "application"
    assert data["status"] == "DRAFT"
    assert data["competitionId"] == competition_id
    assert data["totalPrice"]["totalAmount"] == "0.00"
    assert response["Location"].startswith("/api/v1/applications/")


def test_create_unknown_competition_is_404(auth_client: APIClient) -> None:
    response = _create(auth_client, str(uuid7()))
    assert response.status_code == 404
    assert response["Content-Type"] == "application/problem+json"


def test_list_and_drafts_filter(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    _create(auth_client, competition_id)
    listed = auth_client.get("/api/v1/applications")
    assert listed.status_code == 200
    assert len(listed.data["data"]) == 1
    drafts = auth_client.get("/api/v1/applications?status=DRAFT")
    assert len(drafts.data["data"]) == 1


def test_add_submission_and_retrieve(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    added = auth_client.post(f"/api/v1/applications/{app_id}/submissions")
    assert added.status_code == 201
    assert len(added.data["data"]["submissions"]) == 1
    fetched = auth_client.get(f"/api/v1/applications/{app_id}")
    assert fetched.status_code == 200
    assert len(fetched.data["data"]["submissions"]) == 1


def test_record_consents(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    response = auth_client.put(
        f"/api/v1/applications/{app_id}/consents",
        {"consents": [{"code": "personal_data", "version": "v1"}]},
        format="json",
    )
    assert response.status_code == 200
    assert [c["code"] for c in response.data["data"]["consents"]] == ["personal_data"]


def test_set_payer(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]

    response = auth_client.put(
        f"/api/v1/applications/{app_id}/payer",
        {"lastName": "Иванова", "firstName": "Анна", "middleName": "Сергеевна"},
        format="json",
    )

    assert response.status_code == 200, response.data
    assert response.data["data"]["payer"] == {
        "lastName": "Иванова",
        "firstName": "Анна",
        "middleName": "Сергеевна",
        "fullName": "Иванова Анна Сергеевна",
    }


def test_set_payer_survives_a_reload(auth_client: APIClient) -> None:
    """Three columns, one value object: the name has to come back off the row the same
    way it went in, patronymic and all."""
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    auth_client.put(f"/api/v1/applications/{app_id}/payer", {"lastName": "Иванова", "firstName": "Анна"}, format="json")

    fetched = auth_client.get(f"/api/v1/applications/{app_id}")

    assert fetched.data["data"]["payer"]["fullName"] == "Иванова Анна"
    assert fetched.data["data"]["payer"]["middleName"] is None


def test_a_payer_without_a_given_name_is_a_field_error(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]

    response = auth_client.put(f"/api/v1/applications/{app_id}/payer", {"lastName": "Иванова"}, format="json")

    assert response.status_code == 400, response.data
    assert response["Content-Type"] == "application/problem+json"


def test_a_blank_payer_surname_is_refused_rather_than_crashing(auth_client: APIClient) -> None:
    """`PersonName` lives in the value-object error tree, not the order's, so a name it
    refuses has to come back as a 4xx rather than an unhandled 500."""
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]

    response = auth_client.put(f"/api/v1/applications/{app_id}/payer", {"lastName": "   ", "firstName": "Анна"}, format="json")

    assert 400 <= response.status_code < 500, response.data
    assert response["Content-Type"] == "application/problem+json"


def test_an_application_carries_no_payer_until_one_is_named(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()

    created = _create(auth_client, competition_id)

    assert created.data["data"]["payer"] is None


def test_select_unknown_service_is_404(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    response = auth_client.post(f"/api/v1/applications/{app_id}/services", {"serviceId": str(uuid7())}, format="json")
    assert response.status_code == 404


def test_remove_submission(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    submission_id = auth_client.post(f"/api/v1/applications/{app_id}/submissions").data["data"]["submissions"][0]["submissionId"]
    removed = auth_client.delete(f"/api/v1/applications/{app_id}/submissions/{submission_id}")
    assert removed.status_code == 200
    assert removed.data["data"]["submissions"] == []


def test_cancel(auth_client: APIClient) -> None:
    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    response = auth_client.post(f"/api/v1/applications/{app_id}/cancellation")
    assert response.status_code == 200
    assert response.data["data"]["status"] == "CANCELLED"


def test_receipt_upload_on_draft_succeeds(auth_client: APIClient) -> None:
    # End-to-end wiring of the receipt endpoint: a receipt may be attached upfront,
    # while the order is still a DRAFT in the wizard.
    from django.core.files.uploadedfile import SimpleUploadedFile

    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]
    receipt = SimpleUploadedFile("receipt.pdf", b"%PDF-1.4 paid", content_type="application/pdf")
    response = auth_client.post(f"/api/v1/applications/{app_id}/receipts", {"file": receipt}, format="multipart")
    assert response.status_code == 200, response.data
    assert len(response.data["data"]["paymentReceipts"]) == 1


def test_several_receipts_accumulate_and_one_can_be_taken_back(auth_client: APIClient) -> None:
    # An order's fee is regularly settled by more than one transfer, so posting a
    # second receipt must add to the first rather than overwrite it — and the wrong
    # file must be removable without losing the right one.
    from django.core.files.uploadedfile import SimpleUploadedFile

    competition_id = _seed_open_competition()
    app_id = _create(auth_client, competition_id).data["data"]["id"]

    def _upload(name: str) -> Response:
        upload = SimpleUploadedFile(name, b"%PDF-1.4 paid", content_type="application/pdf")
        return auth_client.post(f"/api/v1/applications/{app_id}/receipts", {"file": upload}, format="multipart")

    _upload("part-one.pdf")
    second = _upload("part-two.pdf")
    assert len(second.data["data"]["paymentReceipts"]) == 2

    wrong_id = second.data["data"]["paymentReceipts"][1]["id"]
    removed = auth_client.delete(f"/api/v1/applications/{app_id}/receipts/{wrong_id}")
    assert removed.status_code == 200, removed.data
    assert [receipt["id"] for receipt in removed.data["data"]["paymentReceipts"]] == [second.data["data"]["paymentReceipts"][0]["id"]]


def test_ownership_isolation() -> None:
    competition_id = _seed_open_competition()
    owner = _auth(APIClient(), email="owner-a@example.com")
    app_id = _create(owner, competition_id).data["data"]["id"]
    other = _auth(APIClient(), email="owner-b@example.com")
    assert other.get(f"/api/v1/applications/{app_id}").status_code == 403
    assert other.get("/api/v1/applications").data["data"] == []
