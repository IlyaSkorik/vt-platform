"""The organizer's side of online judging, through the real HTTP edge.

What these assert, in order of how much it would cost to get wrong: that a festival on
protocols cannot be scored through the API however the request is shaped, that a
configuration write answers with the whole configuration, and that the award scale is
reachable under both judging modes because protocols are written in its vocabulary.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

_SETUP = "/api/v1/staff/judging/setup"
_CRITERIA = "/api/v1/staff/judging/criteria"
_SCALE = "/api/v1/staff/judging/award-scale"
_RULES = "/api/v1/staff/judging/scoring-rules"
_SCOPE = "/api/v1/staff/judging/tally-scope"
_BOARD = "/api/v1/staff/judging/board"
_JURY = "/api/v1/staff/judging/jury"
_OPEN = "/api/v1/staff/judging/scoring/open"
_TALLY = "/api/v1/staff/judging/tally"


class TestTheConfigurationScreen:
    def test_a_festival_that_was_never_configured_reads_as_defaults(self, staff_client: APIClient, competition_id: str) -> None:
        """Opening the screen must leave no row behind and still answer with something
        an organizer can work from."""
        response = staff_client.get(_SETUP, {"competitionId": competition_id})

        assert response.status_code == 200, response.data
        data = response.data["data"]
        assert data["onlineJudging"] is True
        assert len(data["awardScale"]) == 9, "the platform's own degrees are offered"
        assert data["scaleIsBanded"] is False
        assert data["aggregation"] == "AVERAGE"
        assert data["tallyDimensions"] == ["CATEGORY"]

    def test_the_competition_is_required(self, staff_client: APIClient) -> None:
        response = staff_client.get(_SETUP)

        assert response.status_code == 400
        assert response.data["errors"][0]["pointer"] == "/competitionId"

    def test_a_stranger_cannot_read_the_configuration(self, judge_client: APIClient, competition_id: str) -> None:
        assert judge_client.get(_SETUP, {"competitionId": competition_id}).status_code == 403


class TestCriteria:
    def test_a_sheet_is_saved_and_comes_back_with_the_whole_setup(self, staff_client: APIClient, competition_id: str, category_id: str) -> None:
        response = staff_client.put(
            _CRITERIA,
            {
                "competitionId": competition_id,
                "scope": "CATEGORY",
                "targetId": category_id,
                "criteria": [
                    {"name": "Техника", "maxScore": "10", "weight": "2", "sortOrder": 0},
                    {"name": "Артистизм", "maxScore": "10", "weight": "1", "sortOrder": 1},
                ],
            },
            format="json",
        )

        assert response.status_code == 200, response.data
        sheets = response.data["data"]["criteriaSets"]
        assert len(sheets) == 1
        assert sheets[0]["targetName"] == "Вокал"
        assert sheets[0]["maxTotal"] == "30.00", "10×2 + 10×1"

    def test_criteria_keep_their_ids_across_a_rename(self, staff_client: APIClient, competition_id: str, category_id: str) -> None:
        """The property a mark's survival depends on: a renamed criterion is the same
        criterion, and the marks already given against it stay attached."""
        first = staff_client.put(
            _CRITERIA,
            {
                "competitionId": competition_id,
                "scope": "CATEGORY",
                "targetId": category_id,
                "criteria": [{"name": "Техника", "maxScore": "10", "weight": "1", "sortOrder": 0}],
            },
            format="json",
        )
        criterion_id = first.data["data"]["criteriaSets"][0]["criteria"][0]["id"]

        second = staff_client.put(
            _CRITERIA,
            {
                "competitionId": competition_id,
                "scope": "CATEGORY",
                "targetId": category_id,
                "criteria": [{"id": criterion_id, "name": "Техника исполнения", "maxScore": "10", "weight": "1", "sortOrder": 0}],
            },
            format="json",
        )

        renamed = second.data["data"]["criteriaSets"][0]["criteria"][0]
        assert renamed["id"] == criterion_id
        assert renamed["name"] == "Техника исполнения"

    def test_a_criterion_out_of_zero_points_is_refused(self, staff_client: APIClient, competition_id: str, category_id: str) -> None:
        response = staff_client.put(
            _CRITERIA,
            {
                "competitionId": competition_id,
                "scope": "CATEGORY",
                "targetId": category_id,
                "criteria": [{"name": "Ничего", "maxScore": "0", "weight": "1", "sortOrder": 0}],
            },
            format="json",
        )

        assert response.status_code == 400
        assert "балл" in response.data["detail"].lower()


class TestTheAwardScale:
    def test_an_organizer_writes_their_own_places(self, staff_client: APIClient, competition_id: str) -> None:
        response = staff_client.put(
            _SCALE,
            {
                "competitionId": competition_id,
                "tiers": [
                    {"code": "FIRST", "label": "1 место", "minScore": "9", "maxScore": "10", "sortOrder": 0},
                    {"code": "SECOND", "label": "2 место", "minScore": "8", "maxScore": "8.99", "sortOrder": 1},
                ],
            },
            format="json",
        )

        assert response.status_code == 200, response.data
        assert [tier["label"] for tier in response.data["data"]["awardScale"]] == ["1 место", "2 место"]
        assert response.data["data"]["scaleIsBanded"] is True

    def test_overlapping_bands_are_refused_with_a_sentence_a_person_can_read(self, staff_client: APIClient, competition_id: str) -> None:
        response = staff_client.put(
            _SCALE,
            {
                "competitionId": competition_id,
                "tiers": [
                    {"label": "Первая", "minScore": "85", "maxScore": "95", "sortOrder": 0},
                    {"label": "Вторая", "minScore": "90", "maxScore": "99", "sortOrder": 1},
                ],
            },
            format="json",
        )

        assert response.status_code == 400
        assert "пересекаются" in response.data["detail"]

    def test_a_tier_with_no_code_still_gets_one(self, staff_client: APIClient, competition_id: str) -> None:
        """Because a protocol row stores the code, not the label."""
        response = staff_client.put(
            _SCALE,
            {"competitionId": competition_id, "tiers": [{"label": "Гран-при", "minScore": "95", "sortOrder": 0}]},
            format="json",
        )

        assert response.data["data"]["awardScale"][0]["code"] != ""

    def test_the_scale_is_reachable_on_a_protocol_festival_too(self, staff_client: APIClient, competition_id: str) -> None:
        """A festival that judges on paper still writes its protocols in some vocabulary,
        and this is where that vocabulary is configured."""
        settings = staff_client.get(f"/api/v1/competitions/{competition_id}").data["data"]["settings"]
        staff_client.put(
            f"/api/v1/competitions/{competition_id}/settings",
            {**settings, "judgingMode": "PROTOCOLS"},
            format="json",
        )

        response = staff_client.put(
            _SCALE,
            {"competitionId": competition_id, "tiers": [{"label": "1 место", "sortOrder": 0}]},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["data"]["onlineJudging"] is False


class TestScoringRulesAndScope:
    def test_the_aggregation_and_the_dropped_ends_are_saved(self, staff_client: APIClient, competition_id: str) -> None:
        response = staff_client.put(
            _RULES,
            {"competitionId": competition_id, "aggregation": "SUM", "dropHighest": True, "dropLowest": True},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["data"]["aggregation"] == "SUM"
        assert response.data["data"]["dropHighest"] is True

    def test_the_genre_stays_in_the_scope_whatever_is_sent(self, staff_client: APIClient, competition_id: str) -> None:
        """A protocol is a genre's document; a scope without it would put вокал and
        хореография on one sheet."""
        response = staff_client.put(
            _SCOPE,
            {"competitionId": competition_id, "dimensions": ["AGE_CATEGORY"]},
            format="json",
        )

        assert response.data["data"]["tallyDimensions"] == ["CATEGORY", "AGE_CATEGORY"]


class TestTheBoard:
    def test_switching_it_on_mints_a_permanent_link(self, staff_client: APIClient, competition_id: str) -> None:
        response = staff_client.put(
            _BOARD,
            {
                "competitionId": competition_id,
                "enabled": True,
                "visibility": "TOTAL_ONLY",
                "reveal": "AFTER_CLOSE",
            },
            format="json",
        )

        assert response.status_code == 200, response.data
        slug = response.data["data"]["boardSlug"]
        assert slug is not None
        assert response.data["data"]["boardPath"] == f"/board/{slug}"

    def test_the_link_survives_being_switched_off_and_on(self, staff_client: APIClient, competition_id: str) -> None:
        """A projector is pointed at a URL once, often the evening before."""
        body: dict[str, Any] = {
            "competitionId": competition_id,
            "enabled": True,
            "visibility": "TOTAL_ONLY",
            "reveal": "AFTER_CLOSE",
        }
        first = staff_client.put(_BOARD, body, format="json").data["data"]["boardSlug"]
        staff_client.put(_BOARD, {**body, "enabled": False}, format="json")
        again = staff_client.put(_BOARD, body, format="json").data["data"]["boardSlug"]

        assert again == first

    def test_a_board_that_is_off_does_not_resolve_publicly(self, staff_client: APIClient, competition_id: str) -> None:
        body: dict[str, Any] = {
            "competitionId": competition_id,
            "enabled": True,
            "visibility": "TOTAL_ONLY",
            "reveal": "AFTER_CLOSE",
        }
        slug = staff_client.put(_BOARD, body, format="json").data["data"]["boardSlug"]
        assert APIClient().get(f"/api/v1/public/judging/board/{slug}").status_code == 200

        staff_client.put(_BOARD, {**body, "enabled": False}, format="json")

        assert APIClient().get(f"/api/v1/public/judging/board/{slug}").status_code == 404

    def test_an_unknown_slug_is_a_missing_board(self) -> None:
        assert APIClient().get("/api/v1/public/judging/board/NoSuchSlug").status_code == 404


class TestThePanel:
    def test_inviting_seats_somebody_and_hands_back_a_link(self, staff_client: APIClient, competition_id: str) -> None:
        response = staff_client.post(
            _JURY,
            {"competitionId": competition_id, "fullName": "Иванова Анна", "email": "anna@example.ru"},
            format="json",
        )

        assert response.status_code == 201, response.data
        member = response.data["data"]
        assert member["status"] == "INVITED"
        assert member["hasAccount"] is False
        assert member["invitationPath"].startswith("/jury/invite/")

    def test_the_same_address_cannot_be_seated_twice(self, staff_client: APIClient, competition_id: str) -> None:
        """A normal mistake with a panel typed in from a list, so it gets a sentence."""
        body = {"competitionId": competition_id, "fullName": "Иванова Анна", "email": "anna@example.ru"}
        staff_client.post(_JURY, body, format="json")

        second = staff_client.post(_JURY, body, format="json")

        assert second.status_code == 400
        assert "уже есть в составе" in second.data["detail"]

    def test_a_judge_may_be_seated_for_one_genre(self, staff_client: APIClient, competition_id: str, category_id: str) -> None:
        created = staff_client.post(
            _JURY,
            {"competitionId": competition_id, "fullName": "Петров Борис", "email": "boris@example.ru"},
            format="json",
        )
        member_id = created.data["data"]["id"]

        response = staff_client.put(
            f"{_JURY}/{member_id}/assignments",
            {"categoryIds": [category_id]},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["data"]["categoryNames"] == ["Вокал"]

    def test_the_setup_screen_counts_the_panel(self, staff_client: APIClient, competition_id: str) -> None:
        staff_client.post(
            _JURY,
            {"competitionId": competition_id, "fullName": "Иванова Анна", "email": "anna@example.ru"},
            format="json",
        )

        assert staff_client.get(_SETUP, {"competitionId": competition_id}).data["data"]["juryCount"] == 1

    def test_a_stranger_cannot_read_the_panel(self, judge_client: APIClient, competition_id: str) -> None:
        assert judge_client.get(_JURY, {"competitionId": competition_id}).status_code == 403


class TestTheJudgingModeGuard:
    def test_a_protocol_festival_refuses_to_open_an_act(self, staff_client: APIClient, competition_id: str) -> None:
        """The rule that stops a tablet left open from last season writing marks into a
        festival whose organizer has since switched back to protocols."""
        settings = staff_client.get(f"/api/v1/competitions/{competition_id}").data["data"]["settings"]
        staff_client.put(
            f"/api/v1/competitions/{competition_id}/settings",
            {**settings, "judgingMode": "PROTOCOLS"},
            format="json",
        )

        response = staff_client.post(
            _OPEN,
            {"competitionId": competition_id, "submissionId": "00000000-0000-0000-0000-000000000001"},
            format="json",
        )

        assert response.status_code == 409
        assert "онлайн-судейств" in response.data["detail"]


class TestTheTally:
    def test_a_festival_with_no_entries_reckons_to_nothing(self, staff_client: APIClient, competition_id: str) -> None:
        response = staff_client.get(_TALLY, {"competitionId": competition_id})

        assert response.status_code == 200, response.data
        assert response.data["data"]["groups"] == []
        assert response.data["data"]["unawardedCount"] == 0


class TestTheJudgesOwnEndpoints:
    def test_somebody_who_is_not_on_the_panel_gets_no_tasks(self, judge_client: APIClient, competition_id: str) -> None:
        """Not a 403 from a permission class — a judge is *allowed* to ask, and the
        answer is that they hold no seat here."""
        response = judge_client.get("/api/v1/jury/tasks", {"competitionId": competition_id})

        assert response.status_code == 404
        assert "жюри" in response.data["detail"]

    def test_an_unauthenticated_caller_cannot_ask_at_all(self, competition_id: str) -> None:
        assert APIClient().get("/api/v1/jury/tasks", {"competitionId": competition_id}).status_code == 401

    def test_an_unknown_invitation_seats_nobody(self, judge_client: APIClient) -> None:
        response = judge_client.post("/api/v1/jury/invitations/nonsense/accept", format="json")

        assert response.status_code == 404
