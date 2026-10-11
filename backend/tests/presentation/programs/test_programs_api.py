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
from apps.identity.infrastructure.models.user import UserModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler
from apps.teachers.infrastructure.models import TeacherModel

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
    # DRF types `Response.data` as Any; naming the shape here keeps that out of callers.
    created: dict[str, Any] = response.data["data"]
    return created


class TestAccess:
    def test_an_anonymous_caller_is_refused(self, scope: tuple[str, str]) -> None:
        assert APIClient().get(f"{_PROGRAMS}?competitionId={scope[0]}").status_code in (401, 403)

    def test_a_non_staff_user_is_refused(self, outsider_client: APIClient, scope: tuple[str, str]) -> None:
        assert outsider_client.get(f"{_PROGRAMS}?competitionId={scope[0]}").status_code == 403

    def test_listing_requires_a_competition(self, staff_client: APIClient) -> None:
        response = staff_client.get(_PROGRAMS)
        assert response.status_code == 400
        assert response.data["title"] == "Validation failed"


class TestProgramLifecycle:
    def test_a_program_is_created_and_listed(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        created = _create_program(staff_client, scope)
        assert created["name"] == "Вокал, 1 отделение"
        assert created["items"] == []

        listed = staff_client.get(f"{_PROGRAMS}?competitionId={scope[0]}")
        assert listed.status_code == 200
        assert [row["id"] for row in listed.data["data"]] == [created["id"]]
        assert listed.data["meta"]["total"] == 1

    def test_a_program_is_retrieved_and_renamed(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        renamed = staff_client.patch(f"{_PROGRAMS}/{program_id}", {"name": "Вокал, 2 отделение"}, format="json")
        assert renamed.status_code == 200
        assert renamed.data["data"]["name"] == "Вокал, 2 отделение"

    def test_a_blank_name_is_rejected_at_the_edge(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, _nomination_id = scope
        response = staff_client.post(_PROGRAMS, {"competitionId": competition_id, "name": ""}, format="json")
        assert response.status_code == 400

    def test_an_unknown_program_is_a_problem_document(self, staff_client: APIClient) -> None:
        response = staff_client.get(f"{_PROGRAMS}/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.data["title"] == "Resource not found"

    def test_a_program_can_be_deleted(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        assert staff_client.delete(f"{_PROGRAMS}/{program_id}").status_code == 204
        assert staff_client.get(f"{_PROGRAMS}/{program_id}").status_code == 404


class TestBuildingFromANomination:
    def test_candidates_come_from_the_applications_context(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Калинка", seconds=180)
        # Not competing yet: still under review.
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Черновик", seconds=180, status="UNDER_REVIEW")

        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.get(f"{_PROGRAMS}/{program_id}/candidates")
        assert response.status_code == 200
        assert sorted(row["title"] for row in response.data["data"]) == ["Калинка", "Катюша"]

    def test_filling_builds_the_running_order_with_computed_times(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_a_single_act_is_added_by_id_and_carries_its_note(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_an_act_that_is_not_competing_cannot_be_scheduled(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Черновик", seconds=180, status="UNDER_REVIEW")
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"submissionId": submission_id}, format="json")
        assert response.status_code == 422

    def test_the_same_act_twice_is_a_conflict(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"submissionId": submission_id}, format="json")
        again = staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"submissionId": submission_id}, format="json")
        assert again.status_code == 409


class TestBreaks:
    def test_a_break_is_inserted_and_re_times_the_rest(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_a_break_is_edited_and_removed(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Обед", "durationSeconds": 1800}, format="json")
        item_id = created.data["data"]["items"][0]["id"]

        edited = staff_client.patch(f"{_PROGRAMS}/{program_id}/items/{item_id}", {"durationSeconds": 2400}, format="json")
        assert edited.status_code == 200
        assert edited.data["data"]["items"][0]["durationSeconds"] == 2400

        removed = staff_client.delete(f"{_PROGRAMS}/{program_id}/items/{item_id}")
        assert removed.status_code == 200
        assert removed.data["data"]["items"] == []

    def test_a_future_kind_of_service_block_already_works(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/items",
            {"title": "Награждение", "durationSeconds": 1800, "kind": "AWARD"},
            format="json",
        )
        assert response.status_code == 201, response.data
        assert response.data["data"]["items"][0]["kind"] == "AWARD"

    def test_an_unknown_kind_is_rejected(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/items",
            {"title": "Дискотека", "durationSeconds": 600, "kind": "PARTY"},
            format="json",
        )
        assert response.status_code == 400


class TestBufferAndOrder:
    def test_the_buffer_is_changed_and_the_schedule_follows(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_the_order_is_replaced_wholesale(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт A", seconds=100)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт B", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        ids = [item["id"] for item in filled.data["data"]["items"]]

        response = staff_client.put(f"{_PROGRAMS}/{program_id}/items/order", {"itemIds": list(reversed(ids))}, format="json")
        assert response.status_code == 200
        assert [item["id"] for item in response.data["data"]["items"]] == list(reversed(ids))

    def test_reordering_an_unpublished_programme_renumbers_it(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_publishing_freezes_the_numbers(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id, _ids = self._three_act_program(staff_client, scope)
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран"}, format="json")

        assert created.data["data"]["program"]["numbersFrozen"] is True
        assert created.data["data"]["program"]["numbersFrozenAt"] is not None

    def test_reordering_a_published_programme_keeps_the_numbers(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_renumbering_is_a_separate_deliberate_action(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_an_incomplete_order_is_rejected(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт A", seconds=100)
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Акт B", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        filled = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        first = filled.data["data"]["items"][0]["id"]

        response = staff_client.put(f"{_PROGRAMS}/{program_id}/items/order", {"itemIds": [first]}, format="json")
        assert response.status_code == 422

    def test_an_over_long_buffer_is_rejected(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        assert staff_client.patch(f"{_PROGRAMS}/{program_id}", {"bufferSeconds": 7200}, format="json").status_code == 400


class TestTheProgrammeTable:
    def test_the_programme_exposes_every_column_it_can_carry(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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
            "PARTICIPANT_COUNT",
            "AGE_CATEGORY",
            "PARTICIPATION_FORMAT",
            "TEACHERS",
            "ORGANIZATION",
            "CONTACTS",
            "COMMENT",
        ]
        assert {column["key"]: column["label"] for column in program["availableColumns"]}["TEACHERS"] == "Педагог"

    def test_a_row_carries_a_value_for_every_column(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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


class TestHowManyPeopleStandOnStage:
    """The headcount column, which is not the number of performer rows.

    A collective is one row in the entry and the headcount its applicant typed; a solo
    is one row and one person. The organizer needs the second number - it is how many
    chairs, microphones and diplomas the act costs - and ``len(participants)`` answers
    the wrong question for exactly the entries where it matters.
    """

    def test_a_collective_reports_the_headcount_it_stated(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Калинка", seconds=200)
        submission = SubmissionModel.objects.get(id=submission_id)
        submission.participants = [{"id": str(uuid.uuid4()), "display_name": "Ансамбль «Росинка»", "member_count": 14}]
        submission.save(update_fields=["participants"])

        program_id = _create_program(staff_client, scope)["id"]
        item = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill").data["data"]["items"][0]
        assert item["participantCount"] == 14
        assert len(item["participants"]) == 1

    def test_several_performers_without_a_headcount_are_counted_one_each(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Дуэт", seconds=200)
        submission = SubmissionModel.objects.get(id=submission_id)
        # No ``member_count`` at all: entries filled in before the field existed.
        submission.participants = [
            {"id": str(uuid.uuid4()), "display_name": "Иванов Иван"},
            {"id": str(uuid.uuid4()), "display_name": "Петрова Анна"},
        ]
        submission.save(update_fields=["participants"])

        program_id = _create_program(staff_client, scope)["id"]
        item = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill").data["data"]["items"][0]
        assert item["participantCount"] == 2

    def test_a_break_puts_nobody_on_stage(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        added = staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Перерыв", "durationSeconds": 600}, format="json")
        assert added.status_code == 201, added.data
        assert added.data["data"]["items"][0]["participantCount"] == 0


class TestWhoToRingAboutAnAct:
    """The contacts column: the teacher's phone, and the applicant's when there is none."""

    def test_the_teacher_of_record_is_the_number_to_call(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        teacher = TeacherModel.objects.create(
            owner_id=uuid.uuid4(),
            first_name="Мария",
            last_name="Иванова",
            role="COACH",
            phone="+375291112233",
            status="ACTIVE",
        )
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        submission = SubmissionModel.objects.get(id=submission_id)
        submission.teachers = [
            {"first_name": "Мария", "last_name": "Иванова", "middle_name": None, "role": "COACH", "directory_teacher_id": str(teacher.id)}
        ]
        submission.save(update_fields=["teachers"])

        program_id = _create_program(staff_client, scope)["id"]
        item = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill").data["data"]["items"][0]
        assert item["contacts"] == ["+375291112233"]

    def test_an_act_with_no_reachable_teacher_falls_back_to_the_applicant(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        applicant = UserModel.objects.create(
            email="mother@example.com",
            phone="+375337778899",
            first_name="Анна",
            last_name="Петрова",
            locale="ru",
            timezone="Europe/Minsk",
            password_algorithm="argon2",
            password_hash="x",
        )
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        # The seeded teacher is hand-typed: a name on the entry and nowhere to ring.
        SubmissionModel.objects.filter(id=submission_id).update(applicant_id=applicant.id)

        program_id = _create_program(staff_client, scope)["id"]
        item = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill").data["data"]["items"][0]
        assert item["contacts"] == ["+375337778899"]

    def test_an_act_nobody_left_a_number_for_says_so_with_a_blank(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200)
        program_id = _create_program(staff_client, scope)["id"]
        item = staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill").data["data"]["items"][0]
        assert item["contacts"] == []


class TestCustomColumns:
    def test_a_column_is_added_filled_and_published(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_a_column_is_renamed_without_losing_its_values(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_removing_a_column_clears_its_cells(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_a_blank_column_title_is_rejected(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        assert staff_client.post(f"{_PROGRAMS}/{program_id}/columns", {"title": "  "}, format="json").status_code == 400

    def test_a_built_in_column_cannot_be_filled_in_by_hand(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_publishing_an_unknown_custom_column_is_refused(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Чужое", "columns": [f"custom:{uuid.uuid4()}"]},
            format="json",
        )
        assert response.status_code == 404


class TestPdfExport:
    """The organizer prints the programme, choosing which columns go on the page."""

    def _program_with_two_acts(self, staff_client: APIClient, scope: tuple[str, str]) -> str:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200, comment="Выход с точки 3")
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Калинка", seconds=200)
        program_id = str(_create_program(staff_client, scope)["id"])
        staff_client.post(f"{_PROGRAMS}/{program_id}/items/fill")
        return program_id

    def test_the_export_is_a_pdf_attachment(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = self._program_with_two_acts(staff_client, scope)

        response = staff_client.get(f"{_PROGRAMS}/{program_id}/export.pdf?columns=POSITION,TIME,TITLE")
        assert response.status_code == 200, response.content[:200]
        assert response["Content-Type"] == "application/pdf"
        assert "attachment" in response["Content-Disposition"]
        # A real PDF, not an error page rendered with the wrong content type.
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 1000

    def test_every_column_is_exported_when_none_is_chosen(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = self._program_with_two_acts(staff_client, scope)
        response = staff_client.get(f"{_PROGRAMS}/{program_id}/export.pdf")
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")

    def test_a_custom_column_can_be_exported(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = self._program_with_two_acts(staff_client, scope)
        key = staff_client.post(f"{_PROGRAMS}/{program_id}/columns", {"title": "Микрофон"}, format="json").data["data"]["availableColumns"][-1]["key"]

        response = staff_client.get(f"{_PROGRAMS}/{program_id}/export.pdf?columns=TITLE,{key}")
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")

    def test_an_empty_programme_still_exports(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        # A programme is often printed before it is finished; an empty page beats an error.
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.get(f"{_PROGRAMS}/{program_id}/export.pdf?columns=TIME,TITLE")
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")

    def test_an_unknown_column_is_a_problem_document(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = self._program_with_two_acts(staff_client, scope)
        response = staff_client.get(f"{_PROGRAMS}/{program_id}/export.pdf?columns=NOT_A_COLUMN")
        assert response.status_code == 400

    def test_an_unknown_programme_cannot_be_exported(self, staff_client: APIClient) -> None:
        assert staff_client.get(f"{_PROGRAMS}/{uuid.uuid4()}/export.pdf").status_code == 404

    def test_the_export_is_staff_only(self, outsider_client: APIClient, scope: tuple[str, str]) -> None:
        assert outsider_client.get(f"{_PROGRAMS}/{uuid.uuid4()}/export.pdf").status_code == 403


class TestPublicEditions:
    def test_an_edition_is_published_with_its_columns_and_a_copyable_path(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_an_edition_published_without_columns_falls_back_to_the_defaults(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран у сцены"}, format="json")
        assert [column["key"] for column in created.data["data"]["share"]["columns"]] == [
            "POSITION",
            "TIME",
            "PARTICIPANT",
            "TITLE",
        ]

    def test_an_unknown_column_is_rejected(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Нет", "columns": ["TIME", "SOMETHING"]},
            format="json",
        )
        assert response.status_code == 400

    def test_the_columns_of_a_live_link_can_be_changed(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_an_empty_edition_update_is_rejected(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Ведущий"}, format="json")
        share_id = created.data["data"]["share"]["id"]
        assert staff_client.patch(f"{_PROGRAMS}/{program_id}/shares/{share_id}", {}, format="json").status_code == 400

    def test_editions_are_listed_and_can_be_revoked(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран у сцены"}, format="json")
        share_id = created.data["data"]["share"]["id"]

        listed = staff_client.get(f"{_PROGRAMS}/{program_id}/shares")
        assert listed.status_code == 200
        assert [row["id"] for row in listed.data["data"]] == [share_id]

        revoked = staff_client.delete(f"{_PROGRAMS}/{program_id}/shares/{share_id}")
        assert revoked.status_code == 200
        assert revoked.data["data"]["shares"] == []

    def test_an_edition_cannot_select_a_foreign_item(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        response = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Чужое", "itemIds": [str(uuid.uuid4())]},
            format="json",
        )
        assert response.status_code == 422

    def test_the_number_of_editions_is_not_limited(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program_id = _create_program(staff_client, scope)["id"]
        slugs = set()
        for name in ("Звукорежиссёр", "Ведущий", "Жюри", "Экран", "Утреннее отделение"):
            created = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": name}, format="json")
            assert created.status_code == 201
            slugs.add(created.data["data"]["share"]["slug"])
        assert len(slugs) == 5


class TestArrangeEndpoint:
    """Generating the whole running order from rules (VT-86)."""

    def test_rules_in_the_body_build_the_programme(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        for title in ("Калинка", "Катюша"):
            _act(competition_id=competition_id, nomination_id=nomination_id, title=title, seconds=180)
        program = _create_program(staff_client, scope)

        response = staff_client.post(
            f"{_PROGRAMS}/{program['id']}/items/arrange",
            {"grouping": [], "orderWithinGroup": "TITLE", "breakRule": "EVERY_COUNT", "breakAfterItems": 1},
            format="json",
        )

        assert response.status_code == 200, response.data
        items = response.data["data"]["items"]
        assert [item["title"] for item in items] == ["Калинка", "Перерыв", "Катюша"]
        assert [item["kind"] for item in items] == ["PERFORMANCE", "BREAK", "PERFORMANCE"]

    def test_the_rules_come_back_on_the_programme(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=180)
        program = _create_program(staff_client, scope)

        staff_client.post(
            f"{_PROGRAMS}/{program['id']}/items/arrange",
            {"grouping": ["NOMINATION"], "repeatGap": 3, "awardTitle": "Награждение"},
            format="json",
        )
        reloaded = staff_client.get(f"{_PROGRAMS}/{program['id']}")

        arrangement = reloaded.data["data"]["arrangement"]
        assert arrangement["grouping"] == ["NOMINATION"]
        assert arrangement["repeatGap"] == 3
        assert arrangement["awardTitle"] == "Награждение"

    def test_an_empty_body_rebuilds_on_the_saved_rules(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        # The "пересобрать" button: no form is shown, so the programme's own rules are
        # the request.
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=180)
        program = _create_program(staff_client, scope)
        staff_client.post(f"{_PROGRAMS}/{program['id']}/items/arrange", {"openingTitle": "Открытие"}, format="json")

        _act(competition_id=competition_id, nomination_id=nomination_id, title="Калинка", seconds=180)
        response = staff_client.post(f"{_PROGRAMS}/{program['id']}/items/arrange", {}, format="json")

        assert response.status_code == 200, response.data
        assert [item["title"] for item in response.data["data"]["items"]] == ["Открытие", "Калинка", "Катюша"]

    def test_a_programme_never_generated_has_no_rules_on_the_wire(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program = _create_program(staff_client, scope)
        assert program["arrangement"] is None

    def test_an_unknown_rule_is_a_validation_problem(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        program = _create_program(staff_client, scope)

        response = staff_client.post(
            f"{_PROGRAMS}/{program['id']}/items/arrange",
            {"orderWithinGroup": "BY_THE_MOON"},
            format="json",
        )

        assert response.status_code == 400

    def test_a_published_programme_is_refused_with_a_conflict(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=180)
        program = _create_program(staff_client, scope)
        staff_client.post(f"{_PROGRAMS}/{program['id']}/items/arrange", {}, format="json")
        staff_client.post(f"{_PROGRAMS}/{program['id']}/shares", {"name": "Для зала"}, format="json")

        response = staff_client.post(f"{_PROGRAMS}/{program['id']}/items/arrange", {}, format="json")

        assert response.status_code == 409
        assert response.data["type"].endswith("/conflict")
        assert "опубликована" in response.data["detail"]

    def test_an_outsider_cannot_generate_a_programme(
        self,
        staff_client: APIClient,
        outsider_client: APIClient,
        scope: tuple[str, str],
    ) -> None:
        program = _create_program(staff_client, scope)
        response = outsider_client.post(f"{_PROGRAMS}/{program['id']}/items/arrange", {}, format="json")
        assert response.status_code == 403
