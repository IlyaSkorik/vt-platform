"""Integration tests for the public programme screen (anyone-facing).

The contract of a handed-out link: it needs no account, it shows the times the
organizer sees, and it leaks nothing beyond the published lines. Driven end to end so
the routing, the permission classes and the projection are all exercised together.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_PROGRAMS = "/api/v1/staff/programs"
_PUBLIC = "/api/v1/public/programs"
TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def staff_client() -> APIClient:
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "organizer@example.com", "password": _PASSWORD, "firstName": "Ольга", "lastName": "Петрова"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"])))  # type: ignore[arg-type]
    return client


@pytest.fixture
def scope() -> tuple[str, str]:
    competition = CompetitionModel.objects.create(organizer_id=uuid.uuid4(), status="PUBLISHED", title="Весенний фестиваль", season="2025/2026")
    nomination = CategoryModel.objects.create(competition=competition, name="Вокал")
    return str(competition.id), str(nomination.id)


def _act(*, competition_id: str, nomination_id: str, title: str, seconds: int, performer: str, comment: str = "") -> str:
    submission = SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status="ACCEPTED",
        performance={
            "title": title,
            "duration_seconds": seconds,
            "nomination_id": nomination_id,
            "discipline_id": str(uuid.uuid4()),
            "age_category_id": str(uuid.uuid4()),
            "participant_group_id": str(uuid.uuid4()),
            "participation_format_id": str(uuid.uuid4()),
            "comment": comment,
        },
        participants=[{"id": str(uuid.uuid4()), "display_name": performer, "member_count": 1}],
        teachers=[],
    )
    return str(submission.id)


def _published_program(staff_client: APIClient, scope: tuple[str, str], *, name: str = "Для ведущего", item_slice: slice | None = None) -> Any:
    """Build a two-act programme with a break and publish it; returns (slug, items)."""
    competition_id, nomination_id = scope
    _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200, performer="Иванов Иван", comment="Выход с точки 3")
    _act(competition_id=competition_id, nomination_id=nomination_id, title="Калинка", seconds=200, performer="Петров Пётр")
    created = staff_client.post(
        _PROGRAMS,
        {
            "competitionId": competition_id,
            "nominationId": nomination_id,
            "name": "Вокал",
            "startsAt": TEN_AM.isoformat().replace("+00:00", "Z"),
            "bufferSeconds": 40,
        },
        format="json",
    )
    program_id = created.data["data"]["id"]
    filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
    items = filled.data["data"]["items"]
    body: dict[str, Any] = {"name": name}
    if item_slice is not None:
        body["itemIds"] = [item["id"] for item in items[item_slice]]
    share = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", body, format="json")
    return share.data["data"]["share"]["slug"], program_id, items


class TestPublicAccess:
    def test_a_link_needs_no_account(self, staff_client, scope) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        response = APIClient().get(f"{_PUBLIC}/{slug}")
        assert response.status_code == 200
        assert response.data["data"]["name"] == "Для ведущего"

    def test_an_unknown_link_is_an_indistinguishable_404(self, staff_client, scope) -> None:
        _published_program(staff_client, scope)
        response = APIClient().get(f"{_PUBLIC}/Nobody234")
        assert response.status_code == 404
        assert response.data["title"] == "Resource not found"

    def test_a_malformed_link_is_the_same_404(self) -> None:
        assert APIClient().get(f"{_PUBLIC}/!!!").status_code == 404

    def test_a_revoked_link_stops_resolving(self, staff_client, scope) -> None:
        slug, program_id, _items = _published_program(staff_client, scope)
        share_id = staff_client.get(f"{_PROGRAMS}/{program_id}/shares").data["data"][0]["id"]
        staff_client.delete(f"{_PROGRAMS}/{program_id}/shares/{share_id}")
        assert APIClient().get(f"{_PUBLIC}/{slug}").status_code == 404

    def test_deleting_the_programme_takes_the_link_down(self, staff_client, scope) -> None:
        slug, program_id, _items = _published_program(staff_client, scope)
        staff_client.delete(f"{_PROGRAMS}/{program_id}")
        assert APIClient().get(f"{_PUBLIC}/{slug}").status_code == 404


class TestPublicContent:
    def test_the_screen_shows_time_performer_and_work(self, staff_client, scope) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert data["competitionTitle"] == "Весенний фестиваль"
        assert data["nomination"] == "Вокал"
        assert [line["position"] for line in data["items"]] == [1, 2]
        assert [line["title"] for line in data["items"]] == ["Калинка", "Катюша"]
        assert [line["performer"] for line in data["items"]] == ["Петров Пётр", "Иванов Иван"]
        assert data["items"][0]["startsAt"] == datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
        assert data["items"][1]["startsAt"] == datetime(2026, 8, 1, 10, 4, tzinfo=UTC)

    def test_the_public_times_are_the_organizers_times(self, staff_client, scope) -> None:
        slug, program_id, _items = _published_program(staff_client, scope)
        organizer = staff_client.get(f"{_PROGRAMS}/{program_id}").data["data"]
        public = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [item["schedule"]["startsAt"] for item in organizer["items"]] == [line["startsAt"] for line in public["items"]]

    def test_a_partial_edition_publishes_only_its_own_lines(self, staff_client, scope) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope, name="Только второй номер", item_slice=slice(1, 2))
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert len(data["items"]) == 1
        assert data["items"][0]["position"] == 1
        # Its real slot time is preserved, not recomputed from the edition.
        assert data["items"][0]["startsAt"] == datetime(2026, 8, 1, 10, 4, tzinfo=UTC)

    def test_the_public_payload_carries_no_internal_identifiers(self, staff_client, scope) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert "id" not in data
        for line in data["items"]:
            assert "submissionId" not in line
            assert "id" not in line

    def test_breaks_appear_on_the_screen(self, staff_client, scope) -> None:
        slug, program_id, _items = _published_program(staff_client, scope)
        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Перерыв", "durationSeconds": 900}, format="json")
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [line["kind"] for line in data["items"]] == ["PERFORMANCE", "PERFORMANCE", "BREAK"]
        assert data["items"][-1]["title"] == "Перерыв"

    def test_a_whole_programme_edition_keeps_following_the_programme(self, staff_client, scope) -> None:
        slug, program_id, _items = _published_program(staff_client, scope, name="Экран у сцены")
        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Обед", "durationSeconds": 2400}, format="json")
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert len(data["items"]) == 3
