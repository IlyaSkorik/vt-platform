"""The audience's side: the voting page, the vote, and the soft brakes on it."""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.voting.infrastructure.voters import COOKIE_NAME

pytestmark = pytest.mark.django_db

_BALLOTS = "/api/v1/staff/ballots"


def public(slug: str) -> str:
    return f"/api/v1/public/ballots/{slug}"


def visitor() -> APIClient:
    """Somebody in the hall: no account, no cookie yet."""
    return APIClient()


def vote(client: APIClient, slug: str, *nominee_ids: str) -> Any:
    return client.post(f"{public(slug)}/votes", {"nomineeIds": list(nominee_ids)}, format="json")


class TestTheVotingPage:
    def test_anyone_holding_the_link_can_read_it(self, open_ballot: dict[str, Any]) -> None:
        response = visitor().get(public(open_ballot["slug"]))

        assert response.status_code == 200
        assert response.data["data"]["title"] == "Приз зрительских симпатий"
        assert len(response.data["data"]["nominees"]) == 2

    def test_reading_it_makes_the_reader_recognizable(self, open_ballot: dict[str, Any]) -> None:
        response = visitor().get(public(open_ballot["slug"]))

        assert COOKIE_NAME in response.cookies
        cookie = response.cookies[COOKIE_NAME]
        assert cookie["httponly"] is True
        assert cookie["samesite"] == "Lax"

    def test_a_draft_ballot_is_indistinguishable_from_a_dead_link(self, ballot: dict[str, Any]) -> None:
        """A link handed out early must not confirm that something is being prepared."""
        response = visitor().get(public(ballot["slug"]))

        assert response.status_code == 404
        assert COOKIE_NAME not in response.cookies

    def test_an_unknown_slug_mints_nothing(self, open_ballot: dict[str, Any]) -> None:
        """A cookie handed out for a ballot that does not exist is just a tracker."""
        response = visitor().get(public("ZZZZZZZZZZ"))

        assert response.status_code == 404
        assert COOKIE_NAME not in response.cookies

    def test_a_retired_ballot_stops_resolving(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        staff_client.delete(f"{_BALLOTS}/{open_ballot['id']}")

        assert visitor().get(public(open_ballot["slug"])).status_code == 404

    def test_the_body_is_not_cached_by_anything_shared(self, open_ballot: dict[str, Any]) -> None:
        """It carries the reader's own choices."""
        response = visitor().get(public(open_ballot["slug"]))

        assert "private" in response["Cache-Control"]


class TestCastingAVote:
    def test_a_vote_is_counted(self, open_ballot: dict[str, Any]) -> None:
        client = visitor()
        client.get(public(open_ballot["slug"]))
        target = open_ballot["nominees"][0]["id"]

        response = vote(client, open_ballot["slug"], target)

        assert response.status_code == 200, response.data
        assert response.data["data"]["accepted"] == [target]

    def test_the_answer_carries_the_whole_page_so_no_second_request_is_needed(self, open_ballot: dict[str, Any]) -> None:
        client = visitor()
        client.get(public(open_ballot["slug"]))

        response = vote(client, open_ballot["slug"], open_ballot["nominees"][0]["id"])

        assert response.data["data"]["ballot"]["votesLeft"] == 0
        assert response.data["data"]["ballot"]["nominees"][0]["chosen"] is True

    def test_voting_without_reading_the_page_first_still_works(self, open_ballot: dict[str, Any]) -> None:
        """Somebody who deep-links straight to the vote is still a person."""
        response = vote(visitor(), open_ballot["slug"], open_ballot["nominees"][0]["id"])

        assert response.status_code == 200
        assert COOKIE_NAME in response.cookies

    def test_the_same_person_cannot_vote_twice(self, open_ballot: dict[str, Any]) -> None:
        client = visitor()
        target = open_ballot["nominees"][0]["id"]
        vote(client, open_ballot["slug"], target)

        response = vote(client, open_ballot["slug"], target)

        assert response.status_code == 409

    def test_a_second_nominee_is_refused_when_the_ballot_allows_one_vote(self, open_ballot: dict[str, Any]) -> None:
        client = visitor()
        vote(client, open_ballot["slug"], open_ballot["nominees"][0]["id"])

        response = vote(client, open_ballot["slug"], open_ballot["nominees"][1]["id"])

        assert response.status_code == 409

    def test_two_different_people_both_get_to_vote(self, open_ballot: dict[str, Any]) -> None:
        target = open_ballot["nominees"][0]["id"]

        assert vote(visitor(), open_ballot["slug"], target).status_code == 200
        assert vote(visitor(), open_ballot["slug"], target).status_code == 200

    def test_both_votes_are_counted(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        target = open_ballot["nominees"][0]["id"]
        vote(visitor(), open_ballot["slug"], target)
        vote(visitor(), open_ballot["slug"], target)

        detail = staff_client.get(f"{_BALLOTS}/{open_ballot['id']}").data["data"]

        assert detail["nominees"][0]["votes"] == 2
        assert detail["totalVotes"] == 2
        assert detail["voters"] == 2

    def test_a_closed_ballot_takes_no_votes(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        staff_client.post(f"{_BALLOTS}/{open_ballot['id']}/close", format="json")

        response = vote(visitor(), open_ballot["slug"], open_ballot["nominees"][0]["id"])

        assert response.status_code == 422

    def test_a_nominee_from_another_ballot_is_refused(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        other = staff_client.post(_BALLOTS, {"title": "Другое"}, format="json").data["data"]
        added = staff_client.post(f"{_BALLOTS}/{other['id']}/nominees", {"title": "Чужой"}, format="json")
        stranger = added.data["data"]["nominees"][0]["id"]

        response = vote(visitor(), open_ballot["slug"], stranger)

        assert response.status_code == 404

    def test_an_empty_submission_is_refused(self, open_ballot: dict[str, Any]) -> None:
        response = visitor().post(f"{public(open_ballot['slug'])}/votes", {"nomineeIds": []}, format="json")

        assert response.status_code == 400


class TestSeveralVotesEach:
    @pytest.fixture
    def three_vote_ballot(self, staff_client: APIClient) -> dict[str, Any]:
        created = staff_client.post(
            _BALLOTS,
            {"title": "Выберите троих", "votesPerVoter": 3, "reveal": "ALWAYS"},
            format="json",
        )
        ballot_id = created.data["data"]["id"]
        for index in range(4):
            staff_client.post(f"{_BALLOTS}/{ballot_id}/nominees", {"title": f"Участник {index + 1}"}, format="json")
        opened: dict[str, Any] = staff_client.post(f"{_BALLOTS}/{ballot_id}/open", format="json").data["data"]
        return opened

    def test_several_nominees_are_accepted_at_once(self, three_vote_ballot: dict[str, Any]) -> None:
        picks = [row["id"] for row in three_vote_ballot["nominees"][:3]]

        response = vote(visitor(), three_vote_ballot["slug"], *picks)

        assert response.status_code == 200
        assert sorted(response.data["data"]["accepted"]) == sorted(picks)

    def test_more_than_the_allowance_is_refused_before_anything_is_written(self, three_vote_ballot: dict[str, Any]) -> None:
        """All or nothing: nobody is left with two of three votes spent and an error."""
        picks = [row["id"] for row in three_vote_ballot["nominees"]]

        response = vote(visitor(), three_vote_ballot["slug"], *picks)

        assert response.status_code == 409
        page = visitor().get(public(three_vote_ballot["slug"])).data["data"]
        assert page["totalVotes"] == 0

    def test_the_allowance_can_be_spent_across_several_submissions(self, three_vote_ballot: dict[str, Any]) -> None:
        client = visitor()
        rows = three_vote_ballot["nominees"]

        assert vote(client, three_vote_ballot["slug"], rows[0]["id"]).status_code == 200
        second = vote(client, three_vote_ballot["slug"], rows[1]["id"], rows[2]["id"])

        assert second.status_code == 200
        assert second.data["data"]["ballot"]["votesLeft"] == 0

    def test_a_fourth_vote_is_refused(self, three_vote_ballot: dict[str, Any]) -> None:
        client = visitor()
        rows = three_vote_ballot["nominees"]
        vote(client, three_vote_ballot["slug"], rows[0]["id"], rows[1]["id"], rows[2]["id"])

        response = vote(client, three_vote_ballot["slug"], rows[3]["id"])

        assert response.status_code == 409


class TestShowingTheCount:
    def test_the_running_total_is_hidden_by_default(self, open_ballot: dict[str, Any]) -> None:
        """A live scoreboard tells a stuffer exactly how many votes they still need."""
        vote(visitor(), open_ballot["slug"], open_ballot["nominees"][0]["id"])

        page = visitor().get(public(open_ballot["slug"])).data["data"]

        assert page["revealTotals"] is False
        assert page["totalVotes"] is None
        assert page["nominees"][0]["votes"] is None

    def test_it_appears_once_the_vote_is_over(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        vote(visitor(), open_ballot["slug"], open_ballot["nominees"][0]["id"])
        staff_client.post(f"{_BALLOTS}/{open_ballot['id']}/close", format="json")

        page = visitor().get(public(open_ballot["slug"])).data["data"]

        assert page["revealTotals"] is True
        assert page["nominees"][0]["votes"] == 1

    def test_a_ballot_set_to_always_shows_it_while_voting(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        staff_client.patch(f"{_BALLOTS}/{open_ballot['id']}", {"reveal": "ALWAYS"}, format="json")
        vote(visitor(), open_ballot["slug"], open_ballot["nominees"][0]["id"])

        page = visitor().get(public(open_ballot["slug"])).data["data"]

        assert page["nominees"][0]["votes"] == 1

    def test_a_ballot_set_to_never_keeps_it_from_the_public_even_afterwards(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        staff_client.patch(f"{_BALLOTS}/{open_ballot['id']}", {"reveal": "NEVER"}, format="json")
        vote(visitor(), open_ballot["slug"], open_ballot["nominees"][0]["id"])
        staff_client.post(f"{_BALLOTS}/{open_ballot['id']}/close", format="json")

        page = visitor().get(public(open_ballot["slug"])).data["data"]

        assert page["revealTotals"] is False
        assert page["nominees"][0]["votes"] is None


class TestWhatTheReaderIsTold:
    def test_a_closed_ballot_says_so_in_words_for_a_person(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        staff_client.post(f"{_BALLOTS}/{open_ballot['id']}/close", format="json")

        page = visitor().get(public(open_ballot["slug"])).data["data"]

        assert page["open"] is False
        assert page["closedReason"] == "Голосование завершено."

    def test_a_withdrawn_nominee_disappears_from_the_page(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        target = open_ballot["nominees"][0]["id"]
        vote(visitor(), open_ballot["slug"], target)
        staff_client.delete(f"{_BALLOTS}/{open_ballot['id']}/nominees/{target}")

        page = visitor().get(public(open_ballot["slug"])).data["data"]

        assert target not in {row["id"] for row in page["nominees"]}

    def test_a_withdrawn_nominee_keeps_their_votes_in_the_organizers_view(self, staff_client: APIClient, open_ballot: dict[str, Any]) -> None:
        """A result that quietly loses a contestant cannot be audited."""
        target = open_ballot["nominees"][0]["id"]
        vote(visitor(), open_ballot["slug"], target)

        detail = staff_client.delete(f"{_BALLOTS}/{open_ballot['id']}/nominees/{target}").data["data"]

        withdrawn = next(row for row in detail["nominees"] if row["id"] == target)
        assert withdrawn["withdrawn"] is True
        assert withdrawn["votes"] == 1
