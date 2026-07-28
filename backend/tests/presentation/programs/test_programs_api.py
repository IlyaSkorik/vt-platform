"""Integration tests for the organizer Programme constructor REST edge.

Driven through DRF's ``APIClient`` as organization staff against real PostgreSQL: what
only exists at the edge is the staff gate, the wire shape, and the fact that acts come
from the Applications context rather than from a fixture of this one.
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
TEN_AM = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)


def _authenticated(client: APIClient, email: str) -> str:
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": email, "password": _PASSWORD, "firstName": "Ольга", "lastName": "Петрова"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return access


@pytest.fixture
def staff_client() -> APIClient:
    """An organizer: authenticated *and* active organization staff."""
    client = APIClient()
    access = _authenticated(client, "organizer@example.com")
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=str(AccessToken(access)["user_id"])))  # type: ignore[arg-type]
    return client


@pytest.fixture
def outsider_client() -> APIClient:
    """Authenticated, but not staff."""
    client = APIClient()
    _authenticated(client, "participant@example.com")
    return client


@pytest.fixture
def scope() -> tuple[str, str]:
    """A published competition with one nomination; returns (competition_id, nomination_id)."""
    competition = CompetitionModel.objects.create(organizer_id=uuid.uuid4(), status="PUBLISHED", title="Весенний фестиваль", season="2025/2026")
    nomination = CategoryModel.objects.create(competition=competition, name="Вокал")
    return str(competition.id), str(nomination.id)


def _act(
    *,
    competition_id: str,
    nomination_id: str,
    title: str,
    seconds: int,
    performer: str = "Иванов Иван",
    comment: str = "",
    status: str = "ACCEPTED",
) -> str:
    """Seed one competing act in the Applications context."""
    submission = SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status=status,
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
        teachers=[{"first_name": "Мария", "last_name": "Иванова", "middle_name": None, "role": "COACH"}],
    )
    return str(submission.id)


def _create_program(client: APIClient, scope: tuple[str, str], **overrides: Any) -> dict[str, Any]:
    competition_id, nomination_id = scope
    body: dict[str, Any] = {
        "competitionId": competition_id,
        "nominationId": nomination_id,
        "name": "Вокал, 1 отделение",
        "startsAt": TEN_AM.isoformat().replace("+00:00", "Z"),
        **overrides,
    }
    response = client.post(_PROGRAMS, body, format="json")
    assert response.status_code == 201, response.data
    return response.data["data"]


class TestAccess:
    def test_an_anonymous_caller_is_refused(self, scope) -> None:
        assert APIClient().get(f"{_PROGRAMS}?competitionId={scope[0]}").status_code in (401, 403)

    def test_a_non_staff_user_is_refused(self, outsider_client, scope) -> None:
        assert outsider_client.get(f"{_PROGRAMS}?competitionId={scope[0]}").status_code == 403

    def test_listing_requires_a_competition(self, staff_client) -> None:
        response = staff_client.get(_PROGRAMS)
        assert response.status_code == 400
        assert response.data["title"] == "Validation failed"


class TestProgramLifecycle:
    def test_a_program_is_created_and_listed(self, staff_client, scope) -> None:
        created = _create_program(staff_client, scope)
        assert created["name"] == "Вокал, 1 отделение"
        assert created["items"] == []

        listed = staff_client.get(f"{_PROGRAMS}?competitionId={scope[0]}")
        assert listed.status_code == 200
        assert [row["id"] for row in listed.data["data"]] == [created["id"]]
        assert listed.data["meta"]["total"] == 1

    def test_a_program_is_retrieved_and_renamed(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        renamed = staff_client.patch(f"{_PROGRAMS}/{program_id}", {"name": "Вокал, 2 отделение"}, format="json")
        assert renamed.status_code == 200
        assert renamed.data["data"]["name"] == "Вокал, 2 отделение"

    def test_a_blank_name_is_rejected_at_the_edge(self, staff_client, scope) -> None:
        competition_id, _nomination_id = scope
        response = staff_client.post(_PROGRAMS, {"competitionId": competition_id, "name": ""}, format="json")
        assert response.status_code == 400

    def test_an_unknown_program_is_a_problem_document(self, staff_client) -> None:
        response = staff_client.get(f"{_PROGRAMS}/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.data["title"] == "Resource not found"

    def test_a_program_can_be_deleted(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        assert staff_client.delete(f"{_PROGRAMS}/{program_id}").status_code == 204
        assert staff_client.get(f"{_PROGRAMS}/{program_id}").status_code == 404


class TestBuildingFromANomination:
    def test_candidates_come_from_the_applications_context(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Калинка", seconds=180)
        # Not competing yet: still under review.
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Черновик", seconds=180, status="UNDER_REVIEW")

        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.get(f"{_PROGRAMS}/{program_id}/candidates")
        assert response.status_code == 200
        assert sorted(row["title"] for row in response.data["data"]) == ["Калинка", "Катюша"]

    def test_filling_builds_the_running_order_with_computed_times(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт A", seconds=200)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт B", seconds=200)
        program_id = _create_program(staff_client, scope, bufferSeconds=40)["id"]

        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        assert filled.status_code == 200
        items = filled.data["data"]["items"]
        assert [item["schedule"]["position"] for item in items] == [1, 2]
        assert items[0]["schedule"]["startsAt"] == datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
        assert items[1]["schedule"]["startsAt"] == datetime(2026, 8, 1, 10, 4, tzinfo=UTC)
        assert items[0]["schedule"]["slotSeconds"] == 240
        assert items[0]["durationSeconds"] == 200

    def test_a_single_act_is_added_by_id_and_carries_its_note(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        submission_id = _act(
            competition_id=competition_id,
            nomination_id=nomination_id,
            title="Катюша",
            seconds=200,
            performer="Иванов Иван",
            comment="Выход с точки 3",
        )
        program_id = _create_program(staff_client, scope)["id"]

        response = staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"submissionId": submission_id}, format="json")
        assert response.status_code == 201, response.data
        item = response.data["data"]["items"][0]
        assert item["kind"] == "PERFORMANCE"
        assert item["title"] == "Катюша"
        assert item["leadParticipant"] == "Иванов Иван"
        assert item["comment"] == "Выход с точки 3"
        assert item["teachers"] == ["Иванова Мария"]

    def test_an_act_that_is_not_competing_cannot_be_scheduled(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Черновик", seconds=180, status="UNDER_REVIEW")
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"submissionId": submission_id}, format="json")
        assert response.status_code == 422

    def test_the_same_act_twice_is_a_conflict(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"submissionId": submission_id}, format="json")
        again = staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"submissionId": submission_id}, format="json")
        assert again.status_code == 409


class TestBreaks:
    def test_a_break_is_inserted_and_re_times_the_rest(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт A", seconds=180)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт B", seconds=180)
        program_id = _create_program(staff_client, scope)["id"]
        staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")

        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/items",
            {"title": "Перерыв", "durationSeconds": 900, "position": 2},
            format="json",
        )
        assert response.status_code == 201, response.data
        items = response.data["data"]["items"]
        assert [item["kind"] for item in items] == ["PERFORMANCE", "BREAK", "PERFORMANCE"]
        assert items[1]["title"] == "Перерыв"
        assert items[2]["schedule"]["startsAt"] == datetime(2026, 8, 1, 10, 18, tzinfo=UTC)

    def test_a_break_is_edited_and_removed(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Обед", "durationSeconds": 1800}, format="json")
        item_id = created.data["data"]["items"][0]["id"]

        edited = staff_client.patch(f"{_PROGRAMS}/{program_id}/items/{item_id}", {"durationSeconds": 2400}, format="json")
        assert edited.status_code == 200
        assert edited.data["data"]["items"][0]["durationSeconds"] == 2400

        removed = staff_client.delete(f"{_PROGRAMS}/{program_id}/items/{item_id}")
        assert removed.status_code == 200
        assert removed.data["data"]["items"] == []

    def test_a_future_kind_of_service_block_already_works(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/items",
            {"title": "Награждение", "durationSeconds": 1800, "kind": "AWARD"},
            format="json",
        )
        assert response.status_code == 201, response.data
        assert response.data["data"]["items"][0]["kind"] == "AWARD"

    def test_an_unknown_kind_is_rejected(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/items",
            {"title": "Дискотека", "durationSeconds": 600, "kind": "PARTY"},
            format="json",
        )
        assert response.status_code == 400


class TestBufferAndOrder:
    def test_the_buffer_is_changed_and_the_schedule_follows(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт A", seconds=180)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт B", seconds=180)
        program_id = _create_program(staff_client, scope)["id"]
        staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")

        response = staff_client.patch(f"{_PROGRAMS}/{program_id}", {"bufferSeconds": 60}, format="json")
        assert response.status_code == 200
        assert response.data["data"]["bufferSeconds"] == 60
        # The act keeps its own length; only its slot grew.
        assert response.data["data"]["items"][0]["durationSeconds"] == 180
        assert response.data["data"]["items"][1]["schedule"]["startsAt"] == datetime(2026, 8, 1, 10, 4, tzinfo=UTC)

    def test_the_order_is_replaced_wholesale(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт A", seconds=100)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт B", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        ids = [item["id"] for item in filled.data["data"]["items"]]

        response = staff_client.put(f"{_PROGRAMS}/{program_id}/items/order", {"itemIds": list(reversed(ids))}, format="json")
        assert response.status_code == 200
        assert [item["id"] for item in response.data["data"]["items"]] == list(reversed(ids))

    def test_reordering_an_unpublished_programme_renumbers_it(self, staff_client, scope) -> None:
        # Nothing has been handed out yet, so the numbers just follow the order.
        program_id, ids = self._three_act_program(staff_client, scope)

        response = staff_client.put(
            f"{_PROGRAMS}/{program_id}/items/order",
            {"itemIds": [ids[0], ids[2], ids[1]]},
            format="json",
        )
        assert response.status_code == 200
        items = response.data["data"]["items"]
        assert response.data["data"]["numbersFrozen"] is False
        assert [item["id"] for item in items] == [ids[0], ids[2], ids[1]]
        assert [item["number"] for item in items] == [1, 2, 3]

    def test_publishing_freezes_the_numbers(self, staff_client, scope) -> None:
        program_id, _ids = self._three_act_program(staff_client, scope)
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран"}, format="json")

        assert created.data["data"]["program"]["numbersFrozen"] is True
        assert created.data["data"]["program"]["numbersFrozenAt"] is not None

    def test_reordering_a_published_programme_keeps_the_numbers(self, staff_client, scope) -> None:
        # A participant asked to perform later: the row moves, номер 3 stays номер 3, and
        # the programme reads 1, 3, 2 - which is what everybody was told.
        program_id, ids = self._three_act_program(staff_client, scope)
        staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран"}, format="json")

        response = staff_client.put(
            f"{_PROGRAMS}/{program_id}/items/order",
            {"itemIds": [ids[0], ids[2], ids[1]]},
            format="json",
        )
        assert response.status_code == 200
        items = response.data["data"]["items"]
        assert [item["id"] for item in items] == [ids[0], ids[2], ids[1]]
        assert [item["number"] for item in items] == [1, 3, 2]
        # The running order itself is still contiguous - only the numbers jump.
        assert [item["schedule"]["position"] for item in items] == [1, 2, 3]

    def test_renumbering_is_a_separate_deliberate_action(self, staff_client, scope) -> None:
        program_id, ids = self._three_act_program(staff_client, scope)
        staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран"}, format="json")
        staff_client.put(f"{_PROGRAMS}/{program_id}/items/order", {"itemIds": [ids[2], ids[0], ids[1]]}, format="json")

        response = staff_client.post(f"{_PROGRAMS}/{program_id}/items/numbers")
        assert response.status_code == 200, response.data
        assert [item["number"] for item in response.data["data"]["items"]] == [1, 2, 3]

    @staticmethod
    def _three_act_program(staff_client: APIClient, scope: tuple[str, str]) -> tuple[str, list[str]]:
        competition_id, nomination_id = scope
        for index in range(3):
            _act(competition_id=competition_id, nomination_id=nomination_id, title=f"Акт {index}", seconds=120)
        program_id = _create_program(staff_client, scope)["id"]
        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        assert [item["number"] for item in filled.data["data"]["items"]] == [1, 2, 3]
        return program_id, [item["id"] for item in filled.data["data"]["items"]]

    def test_an_incomplete_order_is_rejected(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт A", seconds=100)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт B", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        first = filled.data["data"]["items"][0]["id"]

        response = staff_client.put(f"{_PROGRAMS}/{program_id}/items/order", {"itemIds": [first]}, format="json")
        assert response.status_code == 422

    def test_an_over_long_buffer_is_rejected(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        assert staff_client.patch(f"{_PROGRAMS}/{program_id}", {"bufferSeconds": 7200}, format="json").status_code == 400


class TestTheProgrammeTable:
    def test_the_programme_exposes_every_column_it_can_carry(self, staff_client, scope) -> None:
        program = _create_program(staff_client, scope)
        keys = [column["key"] for column in program["availableColumns"]]
        assert keys == [
            "POSITION",
            "TIME",
            "PARTICIPANT",
            "TITLE",
            "DURATION",
            "NOMINATION",
            "DISCIPLINE",
            "PARTICIPANT_GROUP",
            "AGE_CATEGORY",
            "PARTICIPATION_FORMAT",
            "TEACHERS",
            "ORGANIZATION",
            "COMMENT",
        ]
        assert {column["key"]: column["label"] for column in program["availableColumns"]}["TEACHERS"] == "Педагог"

    def test_a_row_carries_a_value_for_every_column(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(
            competition_id=competition_id,
            nomination_id=nomination_id,
            title="Катюша",
            seconds=200,
            performer="Иванов Иван",
            comment="Выход с точки 3",
        )
        program_id = _create_program(staff_client, scope)["id"]
        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")

        item = filled.data["data"]["items"][0]
        assert item["title"] == "Катюша"
        assert item["leadParticipant"] == "Иванов Иван"
        assert item["teachers"] == ["Иванова Мария"]
        assert item["comment"] == "Выход с точки 3"
        # Every taxonomy column the table offers is resolved, not just the ids.
        for key in ("nomination", "discipline", "ageCategory", "participantGroup", "participationFormat"):
            assert key in item


class TestCustomColumns:
    def test_a_column_is_added_filled_and_published(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        item_id = filled.data["data"]["items"][0]["id"]

        created = staff_client.post(f"{_PROGRAMS}/{program_id}/columns", {"title": "Микрофон"}, format="json")
        assert created.status_code == 201, created.data
        column = created.data["data"]["availableColumns"][-1]
        assert column["label"] == "Микрофон"
        assert column["custom"] is True
        assert column["key"].startswith("custom:")

        written = staff_client.put(
            f"{_PROGRAMS}/{program_id}/items/{item_id}/cells",
            {"values": {column["key"]: "на стойке"}},
            format="json",
        )
        assert written.status_code == 200, written.data
        assert written.data["data"]["items"][0]["customValues"] == {column["key"]: "на стойке"}

        share = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Звукорежиссёр", "columns": ["TIME", "TITLE", column["key"]]},
            format="json",
        )
        assert share.status_code == 201, share.data
        assert [c["label"] for c in share.data["data"]["share"]["columns"]] == ["Время", "Номер", "Микрофон"]

    def test_a_column_is_renamed_without_losing_its_values(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        item_id = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill").data["data"]["items"][0]["id"]
        key = staff_client.post(f"{_PROGRAMS}/{program_id}/columns", {"title": "Микрофон"}, format="json").data["data"]["availableColumns"][-1]["key"]
        staff_client.put(f"{_PROGRAMS}/{program_id}/items/{item_id}/cells", {"values": {key: "на стойке"}}, format="json")

        column_id = key.removeprefix("custom:")
        renamed = staff_client.patch(f"{_PROGRAMS}/{program_id}/columns/{column_id}", {"title": "Микрофон (тип)"}, format="json")
        assert renamed.status_code == 200, renamed.data
        assert renamed.data["data"]["availableColumns"][-1]["label"] == "Микрофон (тип)"
        assert renamed.data["data"]["items"][0]["customValues"] == {key: "на стойке"}

    def test_removing_a_column_clears_its_cells(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        item_id = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill").data["data"]["items"][0]["id"]
        key = staff_client.post(f"{_PROGRAMS}/{program_id}/columns", {"title": "Микрофон"}, format="json").data["data"]["availableColumns"][-1]["key"]
        staff_client.put(f"{_PROGRAMS}/{program_id}/items/{item_id}/cells", {"values": {key: "на стойке"}}, format="json")

        removed = staff_client.delete(f"{_PROGRAMS}/{program_id}/columns/{key.removeprefix('custom:')}")
        assert removed.status_code == 200, removed.data
        assert all(not column["custom"] for column in removed.data["data"]["availableColumns"])
        assert removed.data["data"]["items"][0]["customValues"] == {}

    def test_a_blank_column_title_is_rejected(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        assert staff_client.post(f"{_PROGRAMS}/{program_id}/columns", {"title": "  "}, format="json").status_code == 400

    def test_a_built_in_column_cannot_be_filled_in_by_hand(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        item_id = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill").data["data"]["items"][0]["id"]

        response = staff_client.put(
            f"{_PROGRAMS}/{program_id}/items/{item_id}/cells",
            {"values": {"TITLE": "подменю название"}},
            format="json",
        )
        assert response.status_code == 400

    def test_publishing_an_unknown_custom_column_is_refused(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Чужое", "columns": [f"custom:{uuid.uuid4()}"]},
            format="json",
        )
        assert response.status_code == 404


class TestPublicEditions:
    def test_an_edition_is_published_with_its_columns_and_a_copyable_path(self, staff_client, scope) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт A", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        item_id = filled.data["data"]["items"][0]["id"]

        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {
                "name": "Программа звукорежиссёра",
                "columns": ["TIME", "TITLE", "DURATION", "COMMENT"],
                "itemIds": [item_id],
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        share = response.data["data"]["share"]
        assert share["name"] == "Программа звукорежиссёра"
        assert share["path"] == f"/program/{share['slug']}"
        assert [column["key"] for column in share["columns"]] == ["TIME", "TITLE", "DURATION", "COMMENT"]
        assert share["itemCount"] == 1
        assert share["coversWholeProgram"] is False

    def test_an_edition_published_without_columns_falls_back_to_the_defaults(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран у сцены"}, format="json")
        assert [column["key"] for column in created.data["data"]["share"]["columns"]] == [
            "POSITION",
            "TIME",
            "PARTICIPANT",
            "TITLE",
        ]

    def test_an_unknown_column_is_rejected(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Нет", "columns": ["TIME", "SOMETHING"]},
            format="json",
        )
        assert response.status_code == 400

    def test_the_columns_of_a_live_link_can_be_changed(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Ведущий", "columns": ["TIME", "TITLE"]},
            format="json",
        )
        share = created.data["data"]["share"]

        updated = staff_client.patch(
            f"{_PROGRAMS}/{program_id}/shares/{share['id']}",
            {"columns": ["TIME", "PARTICIPANT", "TITLE"]},
            format="json",
        )
        assert updated.status_code == 200, updated.data
        assert [column["key"] for column in updated.data["data"]["share"]["columns"]] == [
            "TIME",
            "PARTICIPANT",
            "TITLE",
        ]
        # The link itself is permanent, so anything already handed out keeps working.
        assert updated.data["data"]["share"]["slug"] == share["slug"]

    def test_an_empty_edition_update_is_rejected(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Ведущий"}, format="json")
        share_id = created.data["data"]["share"]["id"]
        assert staff_client.patch(f"{_PROGRAMS}/{program_id}/shares/{share_id}", {}, format="json").status_code == 400

    def test_editions_are_listed_and_can_be_revoked(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран у сцены"}, format="json")
        share_id = created.data["data"]["share"]["id"]

        listed = staff_client.get(f"{_PROGRAMS}/{program_id}/shares")
        assert listed.status_code == 200
        assert [row["id"] for row in listed.data["data"]] == [share_id]

        revoked = staff_client.delete(f"{_PROGRAMS}/{program_id}/shares/{share_id}")
        assert revoked.status_code == 200
        assert revoked.data["data"]["shares"] == []

    def test_an_edition_cannot_select_a_foreign_item(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Чужое", "itemIds": [str(uuid.uuid4())]},
            format="json",
        )
        assert response.status_code == 422

    def test_the_number_of_editions_is_not_limited(self, staff_client, scope) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        slugs = set()
        for name in ("Звукорежиссёр", "Ведущий", "Жюри", "Экран", "Утреннее отделение"):
            created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": name}, format="json")
            assert created.status_code == 201
            slugs.add(created.data["data"]["share"]["slug"])
        assert len(slugs) == 5
