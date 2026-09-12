"""The organizer's side of the audience vote, through the real HTTP edge."""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from tests.presentation.voting.conftest import set_modules

pytestmark = pytest.mark.django_db

_BALLOTS = "/api/v1/staff/ballots"


class TestABallotWithoutAFestival:
    def test_a_ballot_can_be_created_naming_no_competition(self, staff_client: APIClient) -> None:
        """The request this whole context exists to answer."""
        response = staff_client.post(_BALLOTS, {"title": "Зрительское голосование"}, format="json")

        assert response.status_code == 201, response.data
        assert response.data["data"]["competitionId"] is None
        assert response.data["data"]["standalone"] is True

    def test_it_gets_a_public_link_of_its_own(self, staff_client: APIClient) -> None:
        response = staff_client.post(_BALLOTS, {"title": "Голосование"}, format="json")

        slug = response.data["data"]["slug"]
        assert len(slug) >= 6
        assert not set(slug) & set("0O1lI")

    def test_two_ballots_never_share_a_link(self, staff_client: APIClient) -> None:
        first = staff_client.post(_BALLOTS, {"title": "Первое"}, format="json")
        second = staff_client.post(_BALLOTS, {"title": "Второе"}, format="json")

        assert first.data["data"]["slug"] != second.data["data"]["slug"]

    def test_the_list_shows_standalone_ballots_too(self, staff_client: APIClient, ballot: dict[str, Any]) -> None:
        response = staff_client.get(_BALLOTS)

        assert response.status_code == 200
        assert ballot["id"] in {row["id"] for row in response.data["data"]}


class TestTheNomineeList:
    def test_nominees_are_numbered_as_they_are_added(self, staff_client: APIClient, ballot: dict[str, Any]) -> None:
        assert [row["position"] for row in ballot["nominees"]] == [1, 2]

    def test_a_nominee_carries_its_own_card(self, staff_client: APIClient, ballot: dict[str, Any]) -> None:
        response = staff_client.post(
            f"{_BALLOTS}/{ballot['id']}/nominees",
            {"title": "Дуэт «Весна»", "subtitle": "«Калинка»", "number": 3},
            format="json",
        )

        added = response.data["data"]["nominees"][-1]
        assert added["title"] == "Дуэт «Весна»"
        assert added["subtitle"] == "«Калинка»"
        assert added["submissionId"] is None

    def test_the_list_can_be_rearranged(self, staff_client: APIClient, ballot: dict[str, Any]) -> None:
        order = [row["id"] for row in reversed(ballot["nominees"])]

        response = staff_client.post(f"{_BALLOTS}/{ballot['id']}/nominees/order", {"order": order}, format="json")

        assert [row["id"] for row in response.data["data"]["nominees"]] == order

    def test_a_reorder_that_loses_somebody_is_refused(self, staff_client: APIClient, ballot: dict[str, Any]) -> None:
        response = staff_client.post(
            f"{_BALLOTS}/{ballot['id']}/nominees/order",
            {"order": [ballot["nominees"][0]["id"]]},
            format="json",
        )

        assert response.status_code == 400

    def test_a_card_can_be_corrected(self, staff_client: APIClient, ballot: dict[str, Any]) -> None:
        nominee_id = ballot["nominees"][0]["id"]

        response = staff_client.patch(
            f"{_BALLOTS}/{ballot['id']}/nominees/{nominee_id}",
            {"title": "Ансамбль «Ритм-2»"},
            format="json",
        )

        assert response.data["data"]["nominees"][0]["title"] == "Ансамбль «Ритм-2»"

    def test_a_nominee_nobody_voted_for_is_simply_removed(self, staff_client: APIClient, ballot: dict[str, Any]) -> None:
        nominee_id = ballot["nominees"][0]["id"]

        response = staff_client.delete(f"{_BALLOTS}/{ballot['id']}/nominees/{nominee_id}")

        assert nominee_id not in {row["id"] for row in response.data["data"]["nominees"]}


class TestOpeningAndClosing:
    def test_a_ballot_with_two_nominees_opens(self, staff_client: APIClient, ballot: dict[str, Any]) -> None:
        response = staff_client.post(f"{_BALLOTS}/{ballot['id']}/open", format="json")

        assert response.status_code == 200
        assert response.data["data"]["status"] == "OPEN"

    def test_a_vote_with_one_option_is_refused(self, staff_client: APIClient) -> None:
        created = staff_client.post(_BALLOTS, {"title": "Одинокое"}, format="json")
        ballot_id = created.data["data"]["id"]
        staff_client.post(f"{_BALLOTS}/{ballot_id}/nominees", {"title": "Единственный"}, format="json")

        response = staff_client.post(f"{_BALLOTS}/{ballot_id}/open", format="json")

        assert response.status_code == 422

    def test_closing_is_one_way(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        staff_client.post(f"{_BALLOTS}/{open_ballot['id']}/close", format="json")

        response = staff_client.post(f"{_BALLOTS}/{open_ballot['id']}/open", format="json")

        assert response.status_code == 422


class TestAuthorization:
    def test_an_organization_without_the_module_is_refused(self, staff_client: APIClient) -> None:
        """Not merely a hidden menu item — the endpoint itself says no."""
        set_modules("PROGRAMS")

        assert staff_client.get(_BALLOTS).status_code == 403

    def test_it_reopens_when_the_module_is_connected(self, staff_client: APIClient) -> None:
        set_modules("PROGRAMS")
        assert staff_client.get(_BALLOTS).status_code == 403

        set_modules("PROGRAMS", "VOTING")

        assert staff_client.get(_BALLOTS).status_code == 200

    def test_an_anonymous_caller_is_refused(self) -> None:
        assert APIClient().get(_BALLOTS).status_code == 401

    def test_an_unknown_ballot_is_a_404(self, staff_client: APIClient) -> None:
        assert staff_client.get(f"{_BALLOTS}/0195c0de-dead-7000-8000-000000000000").status_code == 404

    def test_a_malformed_id_answers_the_same_way(self, staff_client: APIClient) -> None:
        """The caller learns only that they have nothing here."""
        assert staff_client.get(f"{_BALLOTS}/not-a-uuid").status_code == 404
