"""Integration tests for the Competitions REST API v1 (organizer control panel).

Driven through DRF's ``APIClient`` against real PostgreSQL — the full edge is
exercised end to end (serializer → command → handler → repository → response).
Authentication uses a real JWT from the Identity login endpoint; staff status is
granted by provisioning the caller as the organization OWNER through the
Organization composition root (the same seam ``IsOrganizationStaff`` consults).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.competitions.infrastructure.system import Uuid7Generator
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"


def _uuid7() -> uuid.UUID:
    return Uuid7Generator().new()


def _register_and_login(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Org", "lastName": "Aniser"},
        format="json",
    )
    # Mint the session token directly: the login gate refuses unverified accounts,
    # and this BC test only needs an authenticated caller, not the verify flow.
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


def _create_competition(client: APIClient, **overrides: Any) -> Any:
    body: dict[str, Any] = {"organizerId": str(_uuid7()), "title": "Autumn Cup", "season": "2025/2026"}
    body.update(overrides)
    return client.post("/api/v1/competitions", body, format="json")


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_anonymous_is_rejected() -> None:
    response = APIClient().post("/api/v1/competitions", {}, format="json")
    assert response.status_code == 401


def test_participant_cannot_create_competition(participant_client: APIClient) -> None:
    response = _create_competition(participant_client)
    assert response.status_code == 403


def test_participant_cannot_list_competitions(participant_client: APIClient) -> None:
    assert participant_client.get("/api/v1/competitions").status_code == 403


# ---------------------------------------------------------------------------
# CRUD + validation
# ---------------------------------------------------------------------------


def test_staff_can_create_competition(staff_client: APIClient) -> None:
    response = _create_competition(staff_client)
    assert response.status_code == 201
    data = response.data["data"]
    assert data["status"] == "DRAFT"
    assert data["title"] == "Autumn Cup"
    # camelCase wire contract + envelope.
    assert "organizerId" in data
    assert "createdAt" in data
    assert response.data["meta"]["requestId"]


def test_create_validation_error_is_problem_json(staff_client: APIClient) -> None:
    response = staff_client.post("/api/v1/competitions", {"season": "2025/2026"}, format="json")
    assert response.status_code == 400
    assert response["content-type"] == "application/problem+json"
    assert response.data["status"] == 400


def test_get_unknown_competition_returns_404(staff_client: APIClient) -> None:
    response = staff_client.get(f"/api/v1/competitions/{_uuid7()}")
    assert response.status_code == 404
    assert response["content-type"] == "application/problem+json"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_start_from_draft_is_conflict(staff_client: APIClient) -> None:
    """An illegal lifecycle transition (DRAFT → RUNNING) is a 409."""
    competition_id = _create_competition(staff_client).data["data"]["id"]
    response = staff_client.post(f"/api/v1/competitions/{competition_id}/start", {}, format="json")
    assert response.status_code == 409
    assert response["content-type"] == "application/problem+json"


def test_publish_incomplete_draft_is_unprocessable(staff_client: APIClient) -> None:
    """Publishing an unconfigured competition fails the publication-requirements gate (422)."""
    competition_id = _create_competition(staff_client).data["data"]["id"]
    response = staff_client.post(f"/api/v1/competitions/{competition_id}/publish", {}, format="json")
    assert response.status_code == 422
    assert response["content-type"] == "application/problem+json"


def test_mark_ready_incomplete_is_unprocessable(staff_client: APIClient) -> None:
    competition_id = _create_competition(staff_client).data["data"]["id"]
    staff_client.post(f"/api/v1/competitions/{competition_id}/configured", {}, format="json")
    response = staff_client.post(f"/api/v1/competitions/{competition_id}/ready", {}, format="json")
    assert response.status_code == 422


def test_full_organizer_workflow(staff_client: APIClient) -> None:
    base = "/api/v1/competitions"
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"{base}/{competition_id}"

    cat = staff_client.post(f"{detail}/categories", {"name": "Vocal"}, format="json")
    assert cat.status_code == 201
    category_id = cat.data["data"]["categories"][0]["id"]

    staff_client.post(f"{detail}/disciplines", {"categoryId": category_id, "name": "Solo"}, format="json")
    # A participant group is competition-wide, and an age band hangs off the group
    # rather than the category: "7-10" means something different for a soloist than
    # for a twelve-strong ensemble, so the group has to exist first.
    groups = staff_client.post(f"{detail}/participant-groups", {"name": "Solo", "minCount": 1, "maxCount": 1}, format="json")
    assert groups.status_code == 201, groups.data
    participant_group_id = groups.data["data"]["participantGroups"][0]["id"]
    age = staff_client.post(
        f"{detail}/age-categories",
        {"participantGroupId": participant_group_id, "name": "7-10", "minAge": 7, "maxAge": 10},
        format="json",
    )
    assert age.status_code == 201, age.data
    view = staff_client.post(f"{detail}/participation-formats", {"name": "Очно"}, format="json").data["data"]

    combination = {
        "categoryId": view["categories"][0]["id"],
        "disciplineId": view["disciplines"][0]["id"],
        "ageCategoryId": view["ageCategories"][0]["id"],
        "participantGroupId": view["participantGroups"][0]["id"],
        "participationFormatId": view["participationFormats"][0]["id"],
    }
    staff_client.post(f"{detail}/admission-rules", combination, format="json")
    staff_client.post(f"{detail}/pricing-rules", {**combination, "amount": "50.00", "currency": "BYN"}, format="json")
    first = staff_client.post(
        f"{detail}/regulations",
        {"title": "Rules v1", "version": "1.0", "publicationDate": "2026-01-01", "fileReference": "s3://r1.pdf"},
        format="json",
    )
    first_regulation_id = first.data["data"]["regulations"][0]["id"]
    # A second regulation becomes current; switching back to the first is a real
    # state change that exercises the make-current endpoint (not a no-op).
    staff_client.post(
        f"{detail}/regulations",
        {"title": "Rules v2", "version": "2.0", "publicationDate": "2026-02-01", "fileReference": "s3://r2.pdf"},
        format="json",
    )
    made_current = staff_client.post(f"{detail}/regulations/{first_regulation_id}/current", {}, format="json")
    assert made_current.status_code == 200
    assert made_current.data["data"]["currentRegulationId"] == first_regulation_id

    assert staff_client.post(f"{detail}/configured", {}, format="json").status_code == 200
    assert staff_client.post(f"{detail}/ready", {}, format="json").status_code == 200
    published = staff_client.post(f"{detail}/publish", {}, format="json")
    assert published.status_code == 200
    assert published.data["data"]["status"] == "PUBLISHED"
    started = staff_client.post(f"{detail}/start", {}, format="json")
    assert started.data["data"]["status"] == "RUNNING"


# ---------------------------------------------------------------------------
# Routing regression: previously-shadowed detail methods are reachable
# ---------------------------------------------------------------------------


def test_rename_and_delete_category_are_both_reachable(staff_client: APIClient) -> None:
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"
    category_id = staff_client.post(f"{detail}/categories", {"name": "Vocal"}, format="json").data["data"]["categories"][0]["id"]

    renamed = staff_client.patch(f"{detail}/categories/{category_id}", {"name": "Choir"}, format="json")
    assert renamed.status_code == 200
    assert renamed.data["data"]["categories"][0]["name"] == "Choir"

    removed = staff_client.delete(f"{detail}/categories/{category_id}")
    assert removed.status_code == 200
    assert removed.data["data"]["categories"] == []


def test_nomination_waitlist_is_switched_on_and_off_in_place(staff_client: APIClient) -> None:
    """The organizer's whole control over the queue: one toggle on the genre.

    POST and DELETE share the URL because they are the same setting read both ways —
    the route previously shadowed its own detail methods here, which is why this is
    asserted end to end rather than at the handler.
    """
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"
    created = staff_client.post(f"{detail}/categories", {"name": "Vocal"}, format="json")
    category_id = created.data["data"]["categories"][0]["id"]
    assert created.data["data"]["categories"][0]["waitlistEnabled"] is False

    enabled = staff_client.post(f"{detail}/categories/{category_id}/waitlist", {}, format="json")
    assert enabled.status_code == 200, enabled.data
    assert enabled.data["data"]["categories"][0]["waitlistEnabled"] is True

    disabled = staff_client.delete(f"{detail}/categories/{category_id}/waitlist")
    assert disabled.status_code == 200, disabled.data
    assert disabled.data["data"]["categories"][0]["waitlistEnabled"] is False


def test_settings_round_trip_carries_the_media_requirements(staff_client: APIClient) -> None:
    """Save the organizer's media rules and read them back on the detail screen.

    This is the round trip three separate places have to agree on — the write serializer,
    the stored blob, and the detail projection with its own DTO — and the failure mode is
    ugly: a value accepted on save and missing from the projection is a 500 on the page
    the organizer opens next, while every unit test still passes.
    """
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"
    created = staff_client.post(f"{detail}/participation-formats", {"name": "Очно"}, format="json")
    assert created.status_code == 201, created.data
    format_id = created.data["data"]["participationFormats"][0]["id"]

    settings = staff_client.get(detail).data["data"]["settings"]
    payload = {key: value for key, value in settings.items() if key not in {"formatRequirements"}}
    payload["formatRequirements"] = [
        {
            "participationFormatId": format_id,
            "music": {
                "requireUpload": True,
                "allowReplacement": True,
                "allowedFormats": ["mp3"],
                "maxUploadSizeMb": 30,
            },
            # An in-person festival collecting files for the hall's screen: photographs and
            # video under one ceiling, and that ceiling is on their total.
            "media": {
                "mode": "FILE_ONLY",
                "allowedProviders": ["YOUTUBE"],
                "allowReplacement": True,
                # Collected but not demanded: the festival plays what it gets and does not
                # refuse an entry that arrives without a file.
                "requireUpload": False,
                "allowedFormats": ["mp4", "mov", "jpg"],
                "maxTotalSizeMb": 150,
            },
            "paymentReceipt": {
                "requireReceipt": False,
                "allowUploadLater": True,
                "allowReplacement": True,
            },
        }
    ]

    saved = staff_client.put(f"{detail}/settings", payload, format="json")
    assert saved.status_code == 200, saved.data.get("errors") or saved.data

    read_back = staff_client.get(detail)
    assert read_back.status_code == 200, read_back.data
    requirement = read_back.data["data"]["settings"]["formatRequirements"][0]
    assert requirement["music"]["maxUploadSizeMb"] == 30
    assert requirement["media"]["maxTotalSizeMb"] == 150
    assert requirement["media"]["allowedFormats"] == ["mp4", "mov", "jpg"]
    assert requirement["media"]["requireUpload"] is False


def _submission_policy(competition_id: str, participant_group_id: str) -> Any:
    """The policy an applicant's submission is held to, read through the Applications ACL.

    The ACL is the last hop of the settings switch and the only one the applicant
    actually feels: whatever it projects here is what ``Submission.submit`` enforces.
    """
    from apps.applications.domain.value_objects import (
        AgeCategoryId,
        DisciplineId,
        NominationId,
        ParticipantGroupId,
        ParticipationFormatId,
    )
    from apps.applications.domain.value_objects import CompetitionId as AppCompetitionId
    from apps.applications.infrastructure.acl import DjangoCompetitionCatalog

    return DjangoCompetitionCatalog().participation_policy(
        competition_id=AppCompetitionId.from_uuid(uuid.UUID(competition_id)),
        nomination_id=NominationId.from_uuid(_uuid7()),
        discipline_id=DisciplineId.from_uuid(_uuid7()),
        age_category_id=AgeCategoryId.from_uuid(_uuid7()),
        participant_group_id=ParticipantGroupId.from_uuid(uuid.UUID(participant_group_id)),
        participation_format_id=ParticipationFormatId.from_uuid(_uuid7()),
    )


def test_turning_the_teacher_requirement_off_reaches_the_submission_policy(staff_client: APIClient) -> None:
    """«Педагог обязателен», off, is what the applicant's submit is actually held to.

    Four layers have to agree for that switch to mean anything — the write serializer,
    the stored blob, the detail projection, and the Applications ACL that projects it
    onto the submission policy — and the failure mode is silent: the organizer turns the
    requirement off, the screen shows it off, and entries without a teacher are still
    refused at submit.
    """
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"
    group = staff_client.post(f"{detail}/participant-groups", {"name": "Solo", "minCount": 1, "maxCount": 1}, format="json")
    assert group.status_code == 201, group.data
    group_id = group.data["data"]["participantGroups"][0]["id"]

    stored = staff_client.get(detail).data["data"]["settings"]
    # The platform's default: nearly every festival credits a teacher, so it starts on.
    assert stored["requireTeacher"] is True
    assert _submission_policy(competition_id, group_id).requires_teacher is True

    saved = staff_client.put(f"{detail}/settings", {**stored, "requireTeacher": False}, format="json")
    assert saved.status_code == 200, saved.data.get("errors") or saved.data
    assert saved.data["data"]["settings"]["requireTeacher"] is False
    assert staff_client.get(detail).data["data"]["settings"]["requireTeacher"] is False
    assert _submission_policy(competition_id, group_id).requires_teacher is False


def _allows_multiple_performances(competition_id: str) -> bool:
    """The same question the add-performance use case asks, through the same port."""
    from apps.applications.domain.value_objects import CompetitionId as AppCompetitionId
    from apps.applications.infrastructure.acl import DjangoCompetitionCatalog

    return DjangoCompetitionCatalog().allows_multiple_performances(
        competition_id=AppCompetitionId.from_uuid(uuid.UUID(competition_id)),
    )


def test_turning_multiple_performances_off_reaches_the_applications_acl(staff_client: APIClient) -> None:
    """«Несколько выступлений в одной заявке», off, is what the add button obeys.

    The same four layers as the teacher requirement, and the same silent failure mode:
    the organizer turns it off, the screen shows it off, and the wizard keeps offering
    «Добавить выступление» because nothing downstream ever read the flag.
    """
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"

    stored = staff_client.get(detail).data["data"]["settings"]
    # The platform's default: a festival narrows this, it does not have to widen it.
    assert stored["allowMultiplePerformances"] is True
    assert _allows_multiple_performances(competition_id) is True

    saved = staff_client.put(f"{detail}/settings", {**stored, "allowMultiplePerformances": False}, format="json")

    assert saved.status_code == 200, saved.data.get("errors") or saved.data
    assert saved.data["data"]["settings"]["allowMultiplePerformances"] is False
    assert staff_client.get(detail).data["data"]["settings"]["allowMultiplePerformances"] is False
    assert _allows_multiple_performances(competition_id) is False


def test_a_settings_payload_without_the_new_flag_does_not_narrow_the_festival(staff_client: APIClient) -> None:
    """A client that predates the field must not silently forbid second performances."""
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"
    stored = staff_client.get(detail).data["data"]["settings"]

    payload = {key: value for key, value in stored.items() if key != "allowMultiplePerformances"}
    saved = staff_client.put(f"{detail}/settings", payload, format="json")

    assert saved.status_code == 200, saved.data.get("errors") or saved.data
    assert saved.data["data"]["settings"]["allowMultiplePerformances"] is True


def _auto_cancels_unpaid_orders(competition_id: str) -> bool:
    """The same question the unpaid sweep asks, through the same port."""
    from apps.applications.domain.value_objects import CompetitionId as AppCompetitionId
    from apps.applications.infrastructure.acl import DjangoCompetitionCatalog

    return DjangoCompetitionCatalog().auto_cancels_unpaid_orders(
        competition_id=AppCompetitionId.from_uuid(uuid.UUID(competition_id)),
    )


def test_turning_the_unpaid_sweep_off_reaches_the_applications_acl(staff_client: APIClient) -> None:
    """«Отменять неоплаченные заявки», off, is what the sweep and the letter obey."""
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"

    stored = staff_client.get(detail).data["data"]["settings"]
    assert stored["autoCancelUnpaidApplications"] is True
    assert _auto_cancels_unpaid_orders(competition_id) is True

    saved = staff_client.put(f"{detail}/settings", {**stored, "autoCancelUnpaidApplications": False}, format="json")

    assert saved.status_code == 200, saved.data.get("errors") or saved.data
    assert saved.data["data"]["settings"]["autoCancelUnpaidApplications"] is False
    assert staff_client.get(detail).data["data"]["settings"]["autoCancelUnpaidApplications"] is False
    assert _auto_cancels_unpaid_orders(competition_id) is False


def test_a_settings_payload_without_the_sweep_flag_keeps_sweeping(staff_client: APIClient) -> None:
    """An editor that predates the field must not silently stop the sweep."""
    competition_id = _create_competition(staff_client).data["data"]["id"]
    detail = f"/api/v1/competitions/{competition_id}"
    stored = staff_client.get(detail).data["data"]["settings"]

    payload = {key: value for key, value in stored.items() if key != "autoCancelUnpaidApplications"}
    saved = staff_client.put(f"{detail}/settings", payload, format="json")

    assert saved.status_code == 200, saved.data.get("errors") or saved.data
    assert saved.data["data"]["settings"]["autoCancelUnpaidApplications"] is True


# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------


def _png(marker: bytes) -> SimpleUploadedFile:
    """A one-pixel PNG whose trailing bytes differ per call, so two uploads differ."""
    body = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDAT\x78\x9c\x63\x00\x01\x00\x00\x05\x00\x01\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return SimpleUploadedFile(f"poster-{marker.decode()}.png", body + marker, content_type="image/png")


def test_replacing_the_poster_mints_a_new_reference(staff_client: APIClient) -> None:
    """A second upload has to land on its own key, or «Заменить» changes nothing visible.

    With a bucket configured the storage overwrites a repeated key in place and serves it
    back ``immutable`` for a year, so a poster written to a fixed ``poster.png`` keeps the
    reference in the database byte-identical and every browser keeps the first image
    forever — the upload succeeds, the toast appears, and the afisha never changes. The
    filesystem storage the suite runs on hides that by renaming a colliding file, which is
    why this asserts on the shape of the reference and not merely on the two differing.
    """
    competition_id = _create_competition(staff_client).data["data"]["id"]
    poster_endpoint = f"/api/v1/competitions/{competition_id}/branding/poster"

    first = staff_client.post(poster_endpoint, {"file": _png(b"one")}, format="multipart")
    assert first.status_code == 200, first.data
    second = staff_client.post(poster_endpoint, {"file": _png(b"two")}, format="multipart")
    assert second.status_code == 200, second.data

    first_ref = first.data["data"]["branding"]["poster"]
    second_ref = second.data["data"]["branding"]["poster"]
    assert first_ref != second_ref
    # Not the guessable fixed key: that is the exact form a bucket would overwrite.
    assert not first_ref.endswith(f"competitions/{competition_id}/poster.png")
    assert not second_ref.endswith(f"competitions/{competition_id}/poster.png")
