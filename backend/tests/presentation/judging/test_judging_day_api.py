"""The festival day, end to end, over the real REST edge.

The suite next door proves the configuration screens and the security boundary. This
one proves the thing those cannot: that an invited judge can actually sign in, be
handed the acts, mark one, and have the mark reach the organizer's tally and the
protocol they publish.

It is deliberately one long walk rather than a dozen isolated cases. Every step here
depends on the one before — a seat that was never accepted hands out no tasks, a sheet
sent to a closed act never reaches the tally — and splitting it would test the steps
while leaving the chain untested, which is exactly how this surface came to have a
green suite and a jury that could not log in.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.submission import SubmissionModel

pytestmark = pytest.mark.django_db

_JURY = "/api/v1/staff/judging/jury"
_TASKS = "/api/v1/jury/tasks"
_SEATS = "/api/v1/jury/competitions"

#: The address :func:`judge_client` registers under. The invitation has to go to the
#: same one — a seat is held on a named person's behalf.
_JUDGE_EMAIL = "judge@example.com"


def _seed_act(competition_id: str, category_id: str, title: str) -> str:
    """One accepted entry, the shape the Applications context stores it in."""
    submission = SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status="ACCEPTED",
        performance={
            "title": title,
            "duration_seconds": 180,
            "nomination_id": category_id,
            "discipline_id": str(uuid.uuid4()),
            "age_category_id": str(uuid.uuid4()),
            "participant_group_id": str(uuid.uuid4()),
            "participation_format_id": str(uuid.uuid4()),
            "comment": "",
        },
        participants=[{"id": str(uuid.uuid4()), "display_name": "Аня", "member_count": 1}],
        teachers=[],
    )
    return str(submission.id)


def _configure(staff_client: APIClient, competition_id: str, category_id: str) -> None:
    """Criteria out of 20, and a scale with real bands — 18 is a Лауреат I."""
    criteria = staff_client.put(
        "/api/v1/staff/judging/criteria",
        {
            "competitionId": competition_id,
            "scope": "CATEGORY",
            "targetId": category_id,
            "criteria": [
                {"name": "Техника", "maxScore": "10.00", "weight": "1.00", "sortOrder": 0},
                {"name": "Артистизм", "maxScore": "10.00", "weight": "1.00", "sortOrder": 1},
            ],
        },
        format="json",
    )
    assert criteria.status_code == 200, criteria.data
    scale = staff_client.put(
        "/api/v1/staff/judging/award-scale",
        {
            "competitionId": competition_id,
            "tiers": [
                {"code": "LAUREATE_I", "label": "Лауреат I степени", "minScore": "18.00", "sortOrder": 0},
                {"code": "LAUREATE_II", "label": "Лауреат II степени", "minScore": "15.00", "maxScore": "17.99", "sortOrder": 1},
            ],
        },
        format="json",
    )
    assert scale.status_code == 200, scale.data


def _seat_the_judge(staff_client: APIClient, judge_client: APIClient, competition_id: str) -> str:
    """Invite, follow the link, accept. Returns the seat's id."""
    invited = staff_client.post(
        _JURY,
        {"competitionId": competition_id, "fullName": "Иванова Анна", "email": _JUDGE_EMAIL},
        format="json",
    )
    assert invited.status_code == 201, invited.data
    token = str(invited.data["data"]["invitationPath"]).rsplit("/", 1)[-1]

    accepted = judge_client.post(f"/api/v1/jury/invitations/{token}/accept", format="json")
    assert accepted.status_code == 200, accepted.data
    assert accepted.data["data"]["status"] == "ACTIVE"
    return str(accepted.data["data"]["id"])


class TestTheDay:
    """Invitation to protocol, in the order a festival actually happens in."""

    def test_a_judge_finds_their_festival_without_being_staff(
        self, staff_client: APIClient, judge_client: APIClient, competition_id: str, category_id: str
    ) -> None:
        """The way back in. A jury member cannot read the organizer's festival list —
        that is staff-only and answers 403 — so without this endpoint somebody who
        closed the tab has nothing to open."""
        _configure(staff_client, competition_id, category_id)
        _seed_act(competition_id, category_id, "Песня")

        assert judge_client.get("/api/v1/competitions").status_code == 403
        assert judge_client.get(_SEATS).data["data"] == []

        _seat_the_judge(staff_client, judge_client, competition_id)

        seats = judge_client.get(_SEATS)
        assert seats.status_code == 200, seats.data
        assert [item["competitionId"] for item in seats.data["data"]] == [competition_id]
        seat = seats.data["data"][0]
        assert seat["title"] == "Весна талантов"
        assert seat["pendingCount"] == 1
        assert seat["hasOpenAct"] is False

    def test_an_invitation_cannot_be_forwarded_to_somebody_else(self, staff_client: APIClient, judge_client: APIClient, competition_id: str) -> None:
        """The letter is forwardable; the seat is not."""
        invited = staff_client.post(
            _JURY,
            {"competitionId": competition_id, "fullName": "Иванова Анна", "email": "anna@example.ru"},
            format="json",
        )
        token = str(invited.data["data"]["invitationPath"]).rsplit("/", 1)[-1]

        response = judge_client.post(f"/api/v1/jury/invitations/{token}/accept", format="json")

        assert response.status_code == 400
        assert "anna@example.ru" in response.data["detail"]

    def test_a_mark_reaches_the_tally_the_board_and_the_protocol(
        self, staff_client: APIClient, judge_client: APIClient, competition_id: str, category_id: str
    ) -> None:
        _configure(staff_client, competition_id, category_id)
        submission_id = _seed_act(competition_id, category_id, "Песня")
        _seat_the_judge(staff_client, judge_client, competition_id)

        # Before the host opens it, the act is listed and unmarkable.
        pending = judge_client.get(_TASKS, {"competitionId": competition_id})
        assert pending.status_code == 200, pending.data
        assert pending.data["data"][0]["canScore"] is False

        opened = staff_client.post(
            "/api/v1/staff/judging/scoring/open",
            {"competitionId": competition_id, "submissionId": submission_id},
            format="json",
        )
        assert opened.status_code == 200, opened.data

        task: dict[str, Any] = judge_client.get(_TASKS, {"competitionId": competition_id}).data["data"][0]
        assert task["canScore"] is True
        # ADR-0013: the act, never the child.
        assert "Аня" not in str(task)

        card = judge_client.put(
            "/api/v1/jury/scorecards",
            {
                "competitionId": competition_id,
                "submissionId": submission_id,
                "scores": {item["id"]: "9.00" for item in task["criteria"]},
                "comment": "Чисто, но тихо",
            },
            format="json",
        )
        assert card.status_code == 200, card.data
        assert card.data["data"]["myTotal"] == "18.00"

        closed = staff_client.post(
            "/api/v1/staff/judging/scoring/close",
            {"competitionId": competition_id, "submissionId": submission_id},
            format="json",
        )
        assert closed.status_code == 200, closed.data

        # The organizer's tally: 18 of 20, and the band it lands in.
        tally = staff_client.get("/api/v1/staff/judging/tally", {"competitionId": competition_id})
        act = tally.data["data"]["groups"][0]["tallies"][0]
        assert act["score"] == "18.00"
        assert act["awardLabel"] == "Лауреат I степени"
        assert act["submittedCount"] == 1
        assert act["scorecards"][0]["comment"] == "Чисто, но тихо"

        # The judge may still correct a closed act? No — the server refuses.
        refused = judge_client.put(
            "/api/v1/jury/scorecards",
            {
                "competitionId": competition_id,
                "submissionId": submission_id,
                "scores": {item["id"]: "10.00" for item in task["criteria"]},
            },
            format="json",
        )
        assert refused.status_code == 409, refused.data

    def test_the_host_reads_the_programme_in_programme_order(
        self, staff_client: APIClient, judge_client: APIClient, competition_id: str, category_id: str
    ) -> None:
        """Not the tally's order. The tally sorts by score, and a host announcing
        number two must not have it walk up the screen because number three scored
        higher."""
        _configure(staff_client, competition_id, category_id)
        first = _seed_act(competition_id, category_id, "Аллегро")
        second = _seed_act(competition_id, category_id, "Баллада")
        _seat_the_judge(staff_client, judge_client, competition_id)

        # Mark the *second* act well, leaving the first unjudged.
        staff_client.post(
            "/api/v1/staff/judging/scoring/open",
            {"competitionId": competition_id, "submissionId": second},
            format="json",
        )
        task = next(item for item in judge_client.get(_TASKS, {"competitionId": competition_id}).data["data"] if item["submissionId"] == second)
        judge_client.put(
            "/api/v1/jury/scorecards",
            {
                "competitionId": competition_id,
                "submissionId": second,
                "scores": {item["id"]: "10.00" for item in task["criteria"]},
            },
            format="json",
        )

        order = staff_client.get("/api/v1/staff/judging/running-order", {"competitionId": competition_id})

        assert order.status_code == 200, order.data
        titles = [item["title"] for item in order.data["data"]]
        assert titles == ["Аллегро", "Баллада"]
        marked = order.data["data"][1]
        assert marked["status"] == "OPEN"
        assert marked["submittedCount"] == 1
        # The same two acts, the other way round, on the sheet that ranks them.
        tally = staff_client.get("/api/v1/staff/judging/tally", {"competitionId": competition_id})
        assert [item["title"] for item in tally.data["data"]["groups"][0]["tallies"]] == ["Баллада", "Аллегро"]
        assert first in str(order.data["data"])

    def test_pushing_a_tally_with_no_protocol_says_so_rather_than_reporting_nothing(
        self, staff_client: APIClient, judge_client: APIClient, competition_id: str, category_id: str
    ) -> None:
        """The failure this surface shipped with: zero rows changed, read on screen as
        "already up to date", with the protocols still empty at the ceremony."""
        _configure(staff_client, competition_id, category_id)
        submission_id = _seed_act(competition_id, category_id, "Песня")
        _seat_the_judge(staff_client, judge_client, competition_id)
        staff_client.post(
            "/api/v1/staff/judging/scoring/open",
            {"competitionId": competition_id, "submissionId": submission_id},
            format="json",
        )
        task = judge_client.get(_TASKS, {"competitionId": competition_id}).data["data"][0]
        judge_client.put(
            "/api/v1/jury/scorecards",
            {
                "competitionId": competition_id,
                "submissionId": submission_id,
                "scores": {item["id"]: "9.00" for item in task["criteria"]},
            },
            format="json",
        )

        bare = staff_client.post(f"/api/v1/staff/judging/tally/apply?competitionId={competition_id}", format="json")

        assert bare.status_code == 200, bare.data
        assert bare.data["data"]["rowsChanged"] == 0
        assert bare.data["data"]["missingProtocols"] == ["Вокал"]

        applied = staff_client.post(
            f"/api/v1/staff/judging/tally/apply?competitionId={competition_id}",
            {"createMissing": True},
            format="json",
        )

        assert applied.status_code == 200, applied.data
        assert applied.data["data"]["protocolsCreated"] == 1
        assert applied.data["data"]["rowsChanged"] == 1
        assert applied.data["data"]["missingProtocols"] == []

        protocols = staff_client.get("/api/v1/staff/protocols", {"competitionId": competition_id})
        assert protocols.status_code == 200, protocols.data

    def test_the_hall_board_shows_the_result_once_the_act_is_closed(
        self, staff_client: APIClient, judge_client: APIClient, competition_id: str, category_id: str
    ) -> None:
        _configure(staff_client, competition_id, category_id)
        submission_id = _seed_act(competition_id, category_id, "Песня")
        _seat_the_judge(staff_client, judge_client, competition_id)
        board_settings = staff_client.put(
            "/api/v1/staff/judging/board",
            {"competitionId": competition_id, "enabled": True, "visibility": "TOTAL_ONLY", "reveal": "AFTER_CLOSE"},
            format="json",
        )
        slug = board_settings.data["data"]["boardSlug"]

        staff_client.post(
            "/api/v1/staff/judging/scoring/open",
            {"competitionId": competition_id, "submissionId": submission_id},
            format="json",
        )
        task = judge_client.get(_TASKS, {"competitionId": competition_id}).data["data"][0]
        judge_client.put(
            "/api/v1/jury/scorecards",
            {
                "competitionId": competition_id,
                "submissionId": submission_id,
                "scores": {item["id"]: "9.00" for item in task["criteria"]},
            },
            format="json",
        )

        # Still open: under «после закрытия» the hall must not see the score yet.
        during = APIClient().get(f"/api/v1/public/judging/board/{slug}")
        assert during.status_code == 200, during.data
        assert during.data["data"]["current"]["score"] is None

        staff_client.post(
            "/api/v1/staff/judging/scoring/close",
            {"competitionId": competition_id, "submissionId": submission_id},
            format="json",
        )

        after = APIClient().get(f"/api/v1/public/judging/board/{slug}")
        assert after.data["data"]["recent"][0]["score"] == "18.00"
        assert after.data["data"]["recent"][0]["awardLabel"] == "Лауреат I степени"
