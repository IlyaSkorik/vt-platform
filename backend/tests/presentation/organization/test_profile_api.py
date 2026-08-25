"""Integration tests for the Organization profile REST API v1 (staff panel).

Driven through DRF's ``APIClient`` against real PostgreSQL — the full edge is
exercised end to end (serializer → command → handler → repository → response).
Staff status is granted by provisioning the caller as the organization OWNER
through the Organization composition root, the same seam ``IsOrganizationStaff``
consults. The singleton organization itself is seeded by the data migration.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_PROFILE_URL = "/api/v1/organization/profile"


def _register_and_login(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Org", "lastName": "Aniser"},
        format="json",
    )
    return str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)


@pytest.fixture
def staff_client() -> APIClient:
    """An APIClient whose user is an active organization staff member (OWNER)."""
    client = APIClient()
    access = _register_and_login(client, "organizer@example.com")
    user_id = str(AccessToken(access)["user_id"])  # type: ignore[arg-type]
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def participant_client() -> APIClient:
    """An authenticated but non-staff APIClient (a participant)."""
    client = APIClient()
    access = _register_and_login(client, "participant@example.com")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_anonymous_is_rejected() -> None:
    assert APIClient().get(_PROFILE_URL).status_code == 401


def test_participant_cannot_read_profile(participant_client: APIClient) -> None:
    assert participant_client.get(_PROFILE_URL).status_code == 403


def test_participant_cannot_update_profile(participant_client: APIClient) -> None:
    assert participant_client.patch(_PROFILE_URL, {"phone": "123"}, format="json").status_code == 403


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def test_staff_reads_seeded_profile(staff_client: APIClient) -> None:
    response = staff_client.get(_PROFILE_URL)
    assert response.status_code == 200
    data = response.data["data"]
    assert data["name"]
    assert data["slug"]
    assert data["phone"] is None
    assert data["legalInformation"] is None


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_staff_updates_profile_and_it_persists(staff_client: APIClient) -> None:
    response = staff_client.patch(
        _PROFILE_URL,
        {
            "phone": "  +375 29 000-00-00  ",
            "email": "hello@vzlet.ru",
            "website": "https://vzlet.ru",
            "legalInformation": "ООО «Взлёт»",
        },
        format="json",
    )
    assert response.status_code == 200
    data = response.data["data"]
    assert data["phone"] == "+375 29 000-00-00"  # trimmed
    assert data["email"] == "hello@vzlet.ru"
    assert data["legalInformation"] == "ООО «Взлёт»"

    # A subsequent read reflects the persisted change.
    reread = staff_client.get(_PROFILE_URL).data["data"]
    assert reread["website"] == "https://vzlet.ru"


def test_staff_renames_organization(staff_client: APIClient) -> None:
    response = staff_client.patch(_PROFILE_URL, {"name": "Новое имя организации"}, format="json")
    assert response.status_code == 200
    assert response.data["data"]["name"] == "Новое имя организации"

    reread = staff_client.get(_PROFILE_URL).data["data"]
    assert reread["name"] == "Новое имя организации"
    assert reread["slug"]  # slug remains present and unchanged


def test_blank_name_is_rejected(staff_client: APIClient) -> None:
    assert staff_client.patch(_PROFILE_URL, {"name": ""}, format="json").status_code == 400


def test_blank_field_clears_the_value(staff_client: APIClient) -> None:
    staff_client.patch(_PROFILE_URL, {"phone": "+375 29"}, format="json")
    cleared = staff_client.patch(_PROFILE_URL, {"phone": ""}, format="json")
    assert cleared.status_code == 200
    assert cleared.data["data"]["phone"] is None


def test_overlong_field_is_rejected(staff_client: APIClient) -> None:
    response = staff_client.patch(_PROFILE_URL, {"phone": "x" * 201}, format="json")
    assert response.status_code == 400


def test_null_updated_by_is_never_trusted_from_body(staff_client: APIClient) -> None:
    # `updatedBy` is not part of the request contract — the actor comes from the JWT.
    response = staff_client.patch(_PROFILE_URL, {"phone": "1", "updatedBy": str(uuid.uuid4())}, format="json")
    assert response.status_code == 200
    assert response.data["data"]["phone"] == "1"


# ---------------------------------------------------------------------------
# Supporting organization ("при поддержке")
# ---------------------------------------------------------------------------


def test_supporting_organization_round_trips(staff_client: APIClient) -> None:
    """The second block persists as its own entity, beside the organizer's own details.

    The organizer of record and the legal person doing the work are two different
    entities, and both have to reach the public page — so this asserts the two
    blocks do not bleed into each other: the organization keeps its own phone while
    the supporter carries a different one under its own name.
    """
    response = staff_client.patch(
        _PROFILE_URL,
        {
            "phone": "+375 29 111-11-11",
            "legalInformation": "ООО «Мелодия», УНП 191234567",
            "supporter": {
                "name": "  ГУ «Дворец культуры»  ",
                "phone": "+375 17 222-22-22",
                "email": "dk@example.by",
                "legalInformation": "ГУ «Дворец культуры», УНП 100987654",
            },
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    supporter = response.data["data"]["supporter"]
    assert supporter["name"] == "ГУ «Дворец культуры»"  # trimmed
    assert supporter["phone"] == "+375 17 222-22-22"
    assert supporter["legalInformation"] == "ГУ «Дворец культуры», УНП 100987654"
    assert response.data["data"]["phone"] == "+375 29 111-11-11"

    reread = staff_client.get(_PROFILE_URL).data["data"]
    assert reread["supporter"]["email"] == "dk@example.by"
    assert reread["legalInformation"] == "ООО «Мелодия», УНП 191234567"


def test_profile_starts_with_no_supporting_organization(staff_client: APIClient) -> None:
    # `null`, not an object of nulls: "runs its own festivals" is the ordinary case,
    # and the public page decides whether to render the block on exactly this.
    assert staff_client.get(_PROFILE_URL).data["data"]["supporter"] is None


def test_blanking_the_supporter_name_removes_the_whole_block(staff_client: APIClient) -> None:
    """Clearing the name is the only way back to "no supporting entity" — it has to work.

    The domain requires a name, so a named block cannot be edited into an unnamed
    one; if a blank name were rejected instead of collapsing the block, an organizer
    who filled it in once could never undo it.
    """
    staff_client.patch(_PROFILE_URL, {"supporter": {"name": "ГУ «Дворец культуры»", "phone": "+375 17"}}, format="json")
    cleared = staff_client.patch(_PROFILE_URL, {"supporter": {"name": "", "phone": "+375 17"}}, format="json")
    assert cleared.status_code == 200, cleared.data
    # The phone left behind the cleared name goes with it, rather than persisting as
    # an unnamed remnant the public page has no way to render.
    assert cleared.data["data"]["supporter"] is None
    assert staff_client.get(_PROFILE_URL).data["data"]["supporter"] is None


def test_overlong_supporter_field_is_rejected(staff_client: APIClient) -> None:
    response = staff_client.patch(
        _PROFILE_URL,
        {"supporter": {"name": "ГУ «Дворец культуры»", "phone": "x" * 201}},
        format="json",
    )
    assert response.status_code == 400
