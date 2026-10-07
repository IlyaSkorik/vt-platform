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
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
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
    controls: bool = False,
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
    if controls:
        body["controlsRunningOrder"] = True
    if item_slice is not None:
        body["itemIds"] = [item["id"] for item in items[item_slice]]
    share = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", body, format="json")
    return share.data["data"]["share"]["slug"], program_id, items


class TestPublicAccess:
    def test_a_link_needs_no_account(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        response = APIClient().get(f"{_PUBLIC}/{slug}")
        assert response.status_code == 200
        assert response.data["data"]["name"] == "Для ведущего"

    def test_an_unknown_link_is_an_indistinguishable_404(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        _published_program(staff_client, scope)
        response = APIClient().get(f"{_PUBLIC}/Nobody234")
        assert response.status_code == 404
        assert response.data["title"] == "Resource not found"

    def test_a_malformed_link_is_the_same_404(self) -> None:
        assert APIClient().get(f"{_PUBLIC}/!!!").status_code == 404

    def test_a_revoked_link_stops_resolving(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, program_id, _items = _published_program(staff_client, scope)
        share_id = staff_client.get(f"{_PROGRAMS}/{program_id}/shares").data["data"][0]["id"]
        staff_client.delete(f"{_PROGRAMS}/{program_id}/shares/{share_id}")
        assert APIClient().get(f"{_PUBLIC}/{slug}").status_code == 404

    def test_deleting_the_programme_takes_the_link_down(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, program_id, _items = _published_program(staff_client, scope)
        staff_client.delete(f"{_PROGRAMS}/{program_id}")
        assert APIClient().get(f"{_PUBLIC}/{slug}").status_code == 404


class TestTheHostsEdition:
    """The link the organizer hands the host is the one that may drive the day."""

    def _host_link(self, staff_client: APIClient, scope: tuple[str, str]) -> tuple[str, str, list[dict[str, Any]]]:
        """Publish a host edition; returns (slug, program_id, its rows)."""
        slug, program_id, _items = _published_program(
            staff_client,
            scope,
            name="Программа ведущего",
            columns=["POSITION", "TIME", "PARTICIPANT", "TITLE"],
            controls=True,
        )
        rows = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]["rows"]
        return slug, program_id, rows

    def test_the_host_link_says_it_may_control_and_carries_row_handles(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, rows = self._host_link(staff_client, scope)
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]

        assert data["controlsRunningOrder"] is True
        assert all(row["id"] for row in rows)

    def test_a_read_only_link_says_it_may_not_and_carries_no_handles(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope, name="Экран")
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]

        assert data["controlsRunningOrder"] is False
        assert all(row["id"] is None for row in data["rows"])

    def test_the_host_marks_an_act_on_stage_and_everyone_sees_it(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, program_id, rows = self._host_link(staff_client, scope)
        # A second edition of the *same* programme - what the audience screen reads.
        screen_slug = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран"}, format="json").data["data"]["share"]["slug"]

        response = APIClient().put(
            f"{_PUBLIC}/{slug}/rows/{rows[0]['id']}/progress",
            {"progress": "ON_STAGE"},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["data"]["rows"][0]["progress"] == "ON_STAGE"

        # The audience screen is a different link over the same running order.
        screen = APIClient().get(f"{_PUBLIC}/{screen_slug}").data["data"]
        assert screen["rows"][0]["progress"] == "ON_STAGE"

    def test_putting_the_next_act_on_stage_finishes_the_previous_one(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, rows = self._host_link(staff_client, scope)
        client = APIClient()
        client.put(f"{_PUBLIC}/{slug}/rows/{rows[0]['id']}/progress", {"progress": "ON_STAGE"}, format="json")
        second = client.put(f"{_PUBLIC}/{slug}/rows/{rows[1]['id']}/progress", {"progress": "ON_STAGE"}, format="json")

        assert [row["progress"] for row in second.data["data"]["rows"]] == ["PERFORMED", "ON_STAGE"]

    def test_the_host_rearranges_what_is_still_to_come(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, rows = self._host_link(staff_client, scope)
        ids = [row["id"] for row in rows]

        response = APIClient().put(f"{_PUBLIC}/{slug}/order", {"itemIds": list(reversed(ids))}, format="json")
        assert response.status_code == 200, response.data
        assert [row["id"] for row in response.data["data"]["rows"]] == list(reversed(ids))
        # Numbers were frozen at publication, so they travelled with their participants.
        assert [row["cells"][0] for row in response.data["data"]["rows"]] == ["2", "1"]

    def test_a_read_only_link_cannot_drive_the_day(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        # And is refused indistinguishably from a slug that does not exist, so an audience
        # link cannot be probed for whether it happens to be the host's.
        _host_slug, program_id, rows = self._host_link(staff_client, scope)
        screen_slug = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран"}, format="json").data["data"]["share"]["slug"]

        refused = APIClient().put(
            f"{_PUBLIC}/{screen_slug}/rows/{rows[0]['id']}/progress",
            {"progress": "ON_STAGE"},
            format="json",
        )
        assert refused.status_code == 404
        assert APIClient().put(f"{_PUBLIC}/{screen_slug}/order", {"itemIds": [rows[0]["id"]]}, format="json").status_code == 404

    def test_an_unknown_link_cannot_drive_the_day_either(self) -> None:
        response = APIClient().put(f"{_PUBLIC}/Nobody234/rows/{uuid.uuid4()}/progress", {"progress": "ON_STAGE"}, format="json")
        assert response.status_code == 404

    def test_a_link_without_control_is_refused_before_its_body_is_read(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        # Whatever it sends, a link that may not drive the day gets the same 404. The
        # order matters: validating first answered a malformed body with a 400 about the
        # payload, which reads as "your JSON was wrong, try again" and was once reported
        # as the absence of an access check altogether.
        _host_slug, program_id, rows = self._host_link(staff_client, scope)
        screen_slug = staff_client.post(f"{_PROGRAMS}/{program_id}/shares", {"name": "Экран"}, format="json").data["data"]["share"]["slug"]

        for body in ({"progress": "DANCING"}, {}, {"progress": None}):
            refused = APIClient().put(f"{_PUBLIC}/{screen_slug}/rows/{rows[0]['id']}/progress", body, format="json")
            assert refused.status_code == 404, body

        for body in ({"itemIds": "not-a-list"}, {}):
            assert APIClient().put(f"{_PUBLIC}/{screen_slug}/order", body, format="json").status_code == 404, body

        # And an unknown slug answers the same, so neither can be told from the other.
        assert APIClient().put(f"{_PUBLIC}/Nobody234/order", {}, format="json").status_code == 404

    def test_an_unknown_progress_state_is_rejected(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, rows = self._host_link(staff_client, scope)
        response = APIClient().put(
            f"{_PUBLIC}/{slug}/rows/{rows[0]['id']}/progress",
            {"progress": "DANCING"},
            format="json",
        )
        assert response.status_code == 400

    def test_an_incomplete_reorder_from_the_host_is_rejected(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, rows = self._host_link(staff_client, scope)
        response = APIClient().put(f"{_PUBLIC}/{slug}/order", {"itemIds": [rows[0]["id"]]}, format="json")
        assert response.status_code == 422

    def test_the_organizer_can_reset_the_day(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, program_id, rows = self._host_link(staff_client, scope)
        APIClient().put(f"{_PUBLIC}/{slug}/rows/{rows[0]['id']}/progress", {"progress": "PERFORMED"}, format="json")

        reset = staff_client.delete(f"{_PROGRAMS}/{program_id}/progress")
        assert reset.status_code == 200, reset.data
        assert all(item["progress"] == "PENDING" for item in reset.data["data"]["items"])


class TestPublicContent:
    def test_the_screen_is_a_table_of_the_published_columns(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
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

    def test_the_organizer_chooses_which_columns_a_link_shows(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(
            staff_client,
            scope,
            name="Программа звукорежиссёра",
            columns=["TIME", "TITLE", "DURATION", "COMMENT"],
        )
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [column["label"] for column in data["columns"]] == ["Время", "Номер", "Длительность", "Комментарий"]
        assert data["rows"][1]["cells"] == ["10:04", "Катюша", "3:20", "Выход с точки 3"]

    def test_an_unpublished_column_is_absent_from_the_payload(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        # The confidentiality property: whoever holds the link cannot read a column the
        # organizer did not publish.
        slug, _program_id, _items = _published_program(staff_client, scope, columns=["TIME", "TITLE"])
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [column["key"] for column in data["columns"]] == ["TIME", "TITLE"]
        flattened = [cell for row in data["rows"] for cell in row["cells"]]
        assert "Выход с точки 3" not in flattened
        assert "Иванов Иван" not in flattened

    def test_the_public_times_are_the_organizers_times(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, program_id, _items = _published_program(staff_client, scope, columns=["TIME"])
        organizer = staff_client.get(f"{_PROGRAMS}/{program_id}").data["data"]
        public = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [item["schedule"]["startsAt"].strftime("%H:%M") for item in organizer["items"]] == [row["cells"][0] for row in public["rows"]]

    def test_a_partial_edition_publishes_only_its_own_rows(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope, name="Только второй номер", item_slice=slice(1, 2))
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert len(data["rows"]) == 1
        # The participant's own number, not a fresh 1: a cut of the programme is still
        # the programme.
        assert data["rows"][0]["cells"][0] == "2"
        # Its real slot time is preserved, not recomputed from the edition.
        assert data["rows"][0]["cells"][1] == "10:04"

    def test_the_public_payload_carries_no_internal_identifiers(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert "id" not in data
        for row in data["rows"]:
            assert set(row) == {"kind", "cells", "progress", "id"}
            # A read-only edition carries no handle on a row - only the host's does.
            assert row["id"] is None

    def test_breaks_appear_on_the_screen(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, program_id, _items = _published_program(staff_client, scope)
        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Перерыв", "durationSeconds": 900}, format="json")
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert [row["kind"] for row in data["rows"]] == ["PERFORMANCE", "PERFORMANCE", "BREAK"]
        # A break has no participant, so that cell is blank rather than a placeholder.
        assert data["rows"][-1]["cells"] == ["3", "10:08", "", "Перерыв"]

    def test_a_whole_programme_edition_keeps_following_the_programme(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, program_id, _items = _published_program(staff_client, scope, name="Экран у сцены")
        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Обед", "durationSeconds": 2400}, format="json")
        data = APIClient().get(f"{_PUBLIC}/{slug}").data["data"]
        assert len(data["rows"]) == 3


class TestRevalidation:
    """Every open screen asks every few seconds; almost every answer should be "no change".

    This is what makes a five-second poll affordable with a hall full of phones on it, so
    it is a contract of the endpoint rather than an optimization detail: a validator that
    survives an unchanged programme, and one that does not survive a changed one.
    """

    def test_a_read_carries_a_validator(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        response = APIClient().get(f"{_PUBLIC}/{slug}")
        assert response["ETag"]
        # ``no-cache`` is "revalidate", not "do not store" - the client keeps the body and
        # asks whether it is still current.
        assert response["Cache-Control"] == "private, no-cache"

    def test_polling_an_unchanged_programme_costs_a_304(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        first = APIClient().get(f"{_PUBLIC}/{slug}")

        again = APIClient().get(f"{_PUBLIC}/{slug}", HTTP_IF_NONE_MATCH=first["ETag"])
        assert again.status_code == 304
        assert not again.content
        # The validator is repeated, so the next poll can send it back too.
        assert again["ETag"] == first["ETag"]

    def test_a_weak_validator_is_matched_without_its_prefix(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope)
        etag = APIClient().get(f"{_PUBLIC}/{slug}")["ETag"]
        assert etag.startswith('W/"')
        assert APIClient().get(f"{_PUBLIC}/{slug}", HTTP_IF_NONE_MATCH=etag.removeprefix("W/")).status_code == 304

    def test_marking_a_row_invalidates_the_validator(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, _program_id, _items = _published_program(staff_client, scope, name="Программа ведущего", controls=True)
        first = APIClient().get(f"{_PUBLIC}/{slug}")
        row_id = first.data["data"]["rows"][0]["id"]

        APIClient().put(f"{_PUBLIC}/{slug}/rows/{row_id}/progress", {"progress": "ON_STAGE"}, format="json")

        after = APIClient().get(f"{_PUBLIC}/{slug}", HTTP_IF_NONE_MATCH=first["ETag"])
        assert after.status_code == 200, "a row on stage must reach the hall on the next poll"
        assert after["ETag"] != first["ETag"]
        assert after.data["data"]["rows"][0]["progress"] == "ON_STAGE"

    def test_editing_the_programme_invalidates_the_validator(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        slug, program_id, _items = _published_program(staff_client, scope, name="Экран у сцены")
        first = APIClient().get(f"{_PUBLIC}/{slug}")

        staff_client.post(f"{_PROGRAMS}/{program_id}/items", {"title": "Обед", "durationSeconds": 2400}, format="json")

        after = APIClient().get(f"{_PUBLIC}/{slug}", HTTP_IF_NONE_MATCH=first["ETag"])
        assert after.status_code == 200
        assert len(after.data["data"]["rows"]) == 3

    def test_two_editions_of_one_programme_never_share_a_validator(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        """Otherwise one edition's link could revalidate into another's columns."""
        slug_a, program_id, _items = _published_program(staff_client, scope, name="Для жюри", columns=["TIME", "TITLE"])
        share_b = staff_client.post(
            f"{_PROGRAMS}/{program_id}/shares",
            {"name": "Для зала", "columns": ["POSITION", "TITLE"]},
            format="json",
        )
        slug_b = share_b.data["data"]["share"]["slug"]

        etag_a = APIClient().get(f"{_PUBLIC}/{slug_a}")["ETag"]
        response_b = APIClient().get(f"{_PUBLIC}/{slug_b}", HTTP_IF_NONE_MATCH=etag_a)
        assert response_b.status_code == 200
        assert [column["key"] for column in response_b.data["data"]["columns"]] == ["POSITION", "TITLE"]

    def test_a_304_answers_from_one_query(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        """The whole point: an unchanged poll must not load the aggregate or the catalog.

        Asserting the exact count rather than "fewer than a full read" on purpose - if this
        ever grows a second query, the cost lands on every screen every few seconds, and
        that is worth being told about.
        """
        slug, _program_id, _items = _published_program(staff_client, scope)
        etag = APIClient().get(f"{_PUBLIC}/{slug}")["ETag"]

        with CaptureQueriesContext(connection) as unchanged:
            assert APIClient().get(f"{_PUBLIC}/{slug}", HTTP_IF_NONE_MATCH=etag).status_code == 304
        assert len(unchanged.captured_queries) == 1, [query["sql"] for query in unchanged.captured_queries]

        cache.clear()
        with CaptureQueriesContext(connection) as rebuilt:
            assert APIClient().get(f"{_PUBLIC}/{slug}").status_code == 200
        assert len(rebuilt.captured_queries) > 1

    def test_a_revoked_link_is_not_served_from_the_cache(self, staff_client: APIClient, scope: tuple[str, str]) -> None:
        """A link taken down mid-event must stop resolving, warm cache or not."""
        slug, program_id, _items = _published_program(staff_client, scope)
        first = APIClient().get(f"{_PUBLIC}/{slug}")
        assert first.status_code == 200

        share_id = staff_client.get(f"{_PROGRAMS}/{program_id}/shares").data["data"][0]["id"]
        staff_client.delete(f"{_PROGRAMS}/{program_id}/shares/{share_id}")

        assert APIClient().get(f"{_PUBLIC}/{slug}", HTTP_IF_NONE_MATCH=first["ETag"]).status_code == 404
