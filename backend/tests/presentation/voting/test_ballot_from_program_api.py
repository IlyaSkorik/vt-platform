"""A ballot held *inside* a festival: filled from a running order rather than by hand.

The other half of this context. A standalone ballot is typed in or imported from a
spreadsheet; one attached to a festival already has its list — the programme — and
retyping it would be both work and a second chance to get a name wrong.

What these tests pin down is that the copy is a *copy*: what lands on the ballot is
its own nominee, with its own card, which survives whatever happens to the
programme afterwards.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.organization.infrastructure.repositories import DjangoOrganizationRepository

pytestmark = pytest.mark.django_db

_BALLOTS = "/api/v1/staff/ballots"
_PROGRAMS = "/api/v1/staff/programs"


def _organization_id() -> str:
    organization = DjangoOrganizationRepository().get_default()
    assert organization is not None
    return organization.id.json()


@pytest.fixture
def festival() -> tuple[str, str]:
    """A published festival of *this* organization, with one nomination."""
    competition = CompetitionModel.objects.create(
        organizer_id=_organization_id(),
        status="PUBLISHED",
        title="Весенний фестиваль",
        season="2025/2026",
    )
    nomination = CategoryModel.objects.create(competition=competition, name="Вокал")
    return str(competition.id), str(nomination.id)


def _act(competition_id: str, nomination_id: str, *, title: str, performer: str) -> str:
    submission = SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status="ACCEPTED",
        performance={
            "title": title,
            "duration_seconds": 180,
            "nomination_id": nomination_id,
            "discipline_id": str(uuid.uuid4()),
            "age_category_id": str(uuid.uuid4()),
            "participant_group_id": str(uuid.uuid4()),
            "participation_format_id": str(uuid.uuid4()),
        },
        participants=[{"id": str(uuid.uuid4()), "display_name": performer, "member_count": 1}],
        teachers=[],
    )
    return str(submission.id)


@pytest.fixture
def program(staff_client: APIClient, festival: tuple[str, str]) -> dict:
    """A running order of that festival holding two acts."""
    competition_id, nomination_id = festival
    created = staff_client.post(
        _PROGRAMS,
        {"competitionId": competition_id, "nominationId": nomination_id, "name": "Вокал, 1 отделение"},
        format="json",
    )
    assert created.status_code == 201, created.data
    program_id = created.data["data"]["id"]

    for title, performer in (("«Калинка»", "Ансамбль «Ритм»"), ("«Вальс»", "Иванова Мария")):
        submission_id = _act(competition_id, nomination_id, title=title, performer=performer)
        added = staff_client.post(
            f"{_PROGRAMS}/{program_id}/items",
            {"submissionId": submission_id},
            format="json",
        )
        assert added.status_code in (200, 201), added.data

    return staff_client.get(f"{_PROGRAMS}/{program_id}").data["data"]


@pytest.fixture
def festival_ballot(staff_client: APIClient, festival: tuple[str, str]) -> dict:
    """A ballot that names the festival — the case this file is about."""
    created = staff_client.post(
        _BALLOTS,
        {"title": "Приз зрительских симпатий", "competitionId": festival[0]},
        format="json",
    )
    assert created.status_code == 201, created.data
    return created.data["data"]


class TestChoosingAProgramme:
    def test_a_festival_ballot_is_offered_the_festivals_running_orders(self, staff_client: APIClient, festival_ballot: dict, program: dict) -> None:
        response = staff_client.get(f"{_BALLOTS}/{festival_ballot['id']}/programs")

        assert response.status_code == 200
        options = response.data["data"]
        assert program["id"] in {option["id"] for option in options}

    def test_each_option_says_how_many_acts_it_would_bring(self, staff_client: APIClient, festival_ballot: dict, program: dict) -> None:
        """The organizer picks between «День 1» and «День 2» by what is in them."""
        options = staff_client.get(f"{_BALLOTS}/{festival_ballot['id']}/programs").data["data"]

        chosen = next(option for option in options if option["id"] == program["id"])
        assert chosen["nominees"] == 2

    def test_a_standalone_ballot_is_offered_nothing_rather_than_an_error(self, staff_client: APIClient, ballot: dict) -> None:
        """ "There is no festival to take a programme from" is a fact, not a mistake."""
        response = staff_client.get(f"{_BALLOTS}/{ballot['id']}/programs")

        assert response.status_code == 200
        assert response.data["data"] == []


class TestSeeding:
    def test_the_acts_land_on_the_ballot_as_its_own_nominees(self, staff_client: APIClient, festival_ballot: dict, program: dict) -> None:
        response = staff_client.post(
            f"{_BALLOTS}/{festival_ballot['id']}/seed",
            {"programId": program["id"]},
            format="json",
        )

        assert response.status_code == 200, response.data
        nominees = response.data["data"]["nominees"]
        assert [row["title"] for row in nominees] == ["Ансамбль «Ритм»", "Иванова Мария"]
        assert [row["subtitle"] for row in nominees] == ["«Калинка»", "«Вальс»"]

    def test_a_nominee_remembers_which_act_it_came_from(self, staff_client: APIClient, festival_ballot: dict, program: dict) -> None:
        response = staff_client.post(f"{_BALLOTS}/{festival_ballot['id']}/seed", {"programId": program["id"]}, format="json")

        assert all(row["programItemId"] for row in response.data["data"]["nominees"])

    def test_seeding_twice_tops_the_list_up_rather_than_doubling_it(self, staff_client: APIClient, festival_ballot: dict, program: dict) -> None:
        """A running order changes on the day; seeding again should add what is new."""
        staff_client.post(f"{_BALLOTS}/{festival_ballot['id']}/seed", {"programId": program["id"]}, format="json")

        response = staff_client.post(f"{_BALLOTS}/{festival_ballot['id']}/seed", {"programId": program["id"]}, format="json")

        assert len(response.data["data"]["nominees"]) == 2

    def test_the_copy_outlives_the_programme_it_came_from(self, staff_client: APIClient, festival_ballot: dict, program: dict) -> None:
        """The record of what the audience was asked must not change afterwards."""
        staff_client.post(f"{_BALLOTS}/{festival_ballot['id']}/seed", {"programId": program["id"]}, format="json")

        staff_client.delete(f"{_PROGRAMS}/{program['id']}")

        detail = staff_client.get(f"{_BALLOTS}/{festival_ballot['id']}").data["data"]
        assert [row["title"] for row in detail["nominees"]] == ["Ансамбль «Ритм»", "Иванова Мария"]

    def test_a_standalone_ballot_says_to_use_the_file_instead(self, staff_client: APIClient, ballot: dict, program: dict) -> None:
        response = staff_client.post(f"{_BALLOTS}/{ballot['id']}/seed", {"programId": program["id"]}, format="json")

        assert response.status_code == 400
        assert "вручную или из файла" in response.data["detail"]

    def test_another_organizations_programme_cannot_be_harvested(self, staff_client: APIClient, festival_ballot: dict) -> None:
        """Scoped through the competition's own organizer, not through a guessed id."""
        response = staff_client.post(
            f"{_BALLOTS}/{festival_ballot['id']}/seed",
            {"programId": str(uuid.uuid4())},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["data"]["nominees"] == []
