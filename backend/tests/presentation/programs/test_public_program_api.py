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


def _published_program(
    staff_client: APIClient,
    scope: tuple[str, str],
    *,
    name: str = "Для ведущего",
    columns: list[str] | None = None,
    item_slice: slice | None = None,
) -> Any:
    """Build a two-act programme and publish an edition of it; returns (slug, id, items)."""
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
    if columns is not None:
        body["columns"] = columns
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
    def test_the_screen_is_a_table_of_the_published_columns(self, staff_client, scope) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert data["competitionTitle"] == "Весенний фестиваль"
        assert data["nomination"] == "Вокал"
        assert [column["key"] for column in data["columns"]] == ["POSITION", "TIME", "PARTICIPANT", "TITLE"]
        assert [column["label"] for column in data["columns"]] == ["№", "Время", "Участник", "Номер"]
        assert [row["cells"] for row in data["rows"]] == [
            ["1", "10:00", "Петров Пётр", "Калинка"],
            ["2", "10:04", "Иванов Иван", "Катюша"],
        ]

    def test_the_organizer_chooses_which_columns_a_link_shows(self, staff_client, scope) -> None:
        slug, _program_id, _items = _published_program(
            staff_client,
            scope,
            name="Программа звукорежиссёра",
            columns=["TIME", "TITLE", "DURATION", "COMMENT"],
        )
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [column["label"] for column in data["columns"]] == ["Время", "Номер", "Длительность", "Комментарий"]
        assert data["rows"][1]["cells"] == ["10:04", "Катюша", "3:20", "Выход с точки 3"]

    def test_an_unpublished_column_is_absent_from_the_payload(self, staff_client, scope) -> None:
        # The confidentiality property: whoever holds the link cannot read a column the
        # organizer did not publish.
        slug, _program_id, _items = _published_program(staff_client, scope, columns=["TIME", "TITLE"])
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [column["key"] for column in data["columns"]] == ["TIME", "TITLE"]
        flattened = [cell for row in data["rows"] for cell in row["cells"]]
        assert "Выход с точки 3" not in flattened
        assert "Иванов Иван" not in flattened

    def test_the_public_times_are_the_organizers_times(self, staff_client, scope) -> None:
        slug, program_id, _items = _published_program(staff_client, scope, columns=["TIME"])
        organizer = staff_client.get(f"{_PROGRAMS}/{program_id}").data["data"]
        public = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [item["schedule"]["startsAt"].strftime("%H:%M") for item in organizer["items"]] == [row["cells"][0] for row in public["rows"]]

    def test_a_partial_edition_publishes_only_its_own_rows(self, staff_client, scope) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope, name="Только второй номер", item_slice=slice(1, 2))
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert len(data["rows"]) == 1
        assert data["rows"][0]["cells"][0] == "1"
        # Its real slot time is preserved, not recomputed from the edition.
        assert data["rows"][0]["cells"][1] == "10:04"

    def test_the_public_payload_carries_no_internal_identifiers(self, staff_client, scope) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert "id" not in data
        for row in data["rows"]:
            assert set(row) == {"kind", "cells"}

    def test_breaks_appear_on_the_screen(self, staff_client, scope) -> None:
        slug, program_id, _items = _published_program(staff_client, scope)
        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Перерыв", "durationSeconds": 900}, format="json")
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [row["kind"] for row in data["rows"]] == ["PERFORMANCE", "PERFORMANCE", "BREAK"]
        # A break has no participant, so that cell is blank rather than a placeholder.
        assert data["rows"][-1]["cells"] == ["3", "10:08", "", "Перерыв"]

    def test_a_whole_programme_edition_keeps_following_the_programme(self, staff_client, scope) -> None:
        slug, program_id, _items = _published_program(staff_client, scope, name="Экран у сцены")
        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Обед", "durationSeconds": 2400}, format="json")
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert len(data["rows"]) == 3
