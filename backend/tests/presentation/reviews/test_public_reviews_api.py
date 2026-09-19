"""Сторона посетителя: страница за QR-кодом и сам отзыв.

Здесь проверяется то, ради чего блок существует: человек в фойе сканирует код,
пишет пару фраз и уходит. Аккаунта у него нет, ссылка — единственный ключ, а
согласие на обработку персональных данных — единственное, без чего отзыв не
сохраняется.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.reviews.domain.value_objects import PHOTOS_MAX
from tests.presentation.reviews.conftest import organization_id

pytestmark = pytest.mark.django_db

_CONSENT_TYPE = "review_personal_data"
_CONSENT = "1.0"
_PAGE = "/api/v1/staff/reviews/page"

# A one-pixel PNG: the smallest thing the upload path will accept as a photograph.
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082"
)


def visitor() -> APIClient:
    """Somebody in the foyer: no account, no session."""
    return APIClient()


def public(slug: str) -> str:
    return f"/api/v1/public/reviews/{slug}"


def leave(client: APIClient, slug: str, **fields: Any) -> Any:
    payload: dict[str, Any] = {"text": "Спасибо, было здорово!", "consentType": _CONSENT_TYPE, "consentVersion": _CONSENT, "consentAccepted": True}
    payload.update(fields)
    return client.post(f"{public(slug)}/entries", payload, format="multipart")


def photo(name: str = "hall.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _PNG, content_type="image/png")


class TestThePageBehindTheCode:
    def test_anyone_holding_the_link_can_read_it(self, page: dict[str, Any]) -> None:
        response = visitor().get(public(page["slug"]))

        assert response.status_code == 200
        assert response.data["data"]["accepting"] is True
        assert response.data["data"]["organizationName"]

    def test_an_unknown_slug_is_a_dead_link(self, page: dict[str, Any]) -> None:
        assert visitor().get(public("ZZZZZZZZZZ")).status_code == 404

    def test_the_page_carries_no_internal_identifiers(self, page: dict[str, Any]) -> None:
        """Страница открыта всем: идентификаторы организации ей ни к чему."""
        body = visitor().get(public(page["slug"])).data["data"]

        assert "organizationId" not in body
        assert "id" not in body

    def test_a_closed_page_still_answers_and_says_so(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        """Баннер уже напечатан — ссылка объясняется, а не умирает."""
        staff_client.patch(_PAGE, {"accepting": False}, format="json")

        response = visitor().get(public(page["slug"]))

        assert response.status_code == 200
        assert response.data["data"]["accepting"] is False


class TestLeavingAReview:
    def test_a_few_words_are_enough(self, page: dict[str, Any]) -> None:
        response = leave(visitor(), page["slug"])

        assert response.status_code == 201, response.data
        assert response.data["data"]["text"] == "Спасибо, было здорово!"
        assert response.data["data"]["authorName"] is None

    def test_the_name_is_optional(self, page: dict[str, Any]) -> None:
        """Спрашивать имя обязательно — способ перестать получать честные отзывы."""
        blank = leave(visitor(), page["slug"], authorName="")
        signed = leave(visitor(), page["slug"], authorName="Мария")

        assert blank.data["data"]["authorName"] is None
        assert signed.data["data"]["authorName"] == "Мария"

    def test_without_consent_nothing_is_stored(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        response = leave(visitor(), page["slug"], consentAccepted=False)

        assert response.status_code == 422
        assert response.data["title"] == "Consent is required to store a review"
        assert staff_client.get("/api/v1/staff/reviews").data["data"] == []

    def test_the_accepted_wording_is_recorded_with_the_note(self, page: dict[str, Any]) -> None:
        """Версия согласия — часть записи: тексты версионируются и не переписываются."""
        response = leave(visitor(), page["slug"])

        assert response.data["data"]["consentType"] == _CONSENT_TYPE
        assert response.data["data"]["consentVersion"] == _CONSENT
        assert response.data["data"]["consentAcceptedAt"] is not None

    def test_an_empty_note_is_refused(self, page: dict[str, Any]) -> None:
        response = leave(visitor(), page["slug"], text="   ")

        assert response.status_code == 400

    def test_a_closed_page_does_not_take_notes(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        staff_client.patch(_PAGE, {"accepting": False}, format="json")

        response = leave(visitor(), page["slug"])

        assert response.status_code == 422
        assert response.data["title"] == "This page no longer collects reviews"

    def test_an_unknown_slug_takes_nothing(self, page: dict[str, Any]) -> None:
        assert leave(visitor(), "ZZZZZZZZZZ").status_code == 404


class TestThePhotographs:
    def test_a_photograph_comes_back_as_an_address(self, page: dict[str, Any]) -> None:
        response = leave(visitor(), page["slug"], photos=[photo()])

        assert response.status_code == 201, response.data
        photos = response.data["data"]["photos"]
        assert len(photos) == 1
        assert photos[0].startswith(("/", "http"))

    def test_more_than_the_limit_is_refused(self, page: dict[str, Any]) -> None:
        response = leave(visitor(), page["slug"], photos=[photo(f"{index}.png") for index in range(PHOTOS_MAX + 1)])

        assert response.status_code == 400
        assert str(PHOTOS_MAX) in response.data["detail"]

    def test_something_that_is_not_an_image_is_refused(self, page: dict[str, Any]) -> None:
        document = SimpleUploadedFile("rider.pdf", b"%PDF-1.4", content_type="application/pdf")

        response = leave(visitor(), page["slug"], photos=[document])

        assert response.status_code == 400

    def test_a_rejected_note_leaves_no_files_behind(self, settings: Any, page: dict[str, Any]) -> None:
        """Фотографии пишутся до проверки текста; отказ не должен оставлять мусор."""
        import pathlib

        leave(visitor(), page["slug"], text="   ", photos=[photo()])

        written = list(pathlib.Path(settings.MEDIA_ROOT).rglob("*.png"))
        assert written == []


class TestTheBrake:
    def test_a_flood_from_one_place_is_slowed_down(self, page: dict[str, Any]) -> None:
        """Человек у баннера отправляет одну заметку; шесть в минуту — уже не человек."""
        visitor_client = visitor()
        codes = [leave(visitor_client, page["slug"]).status_code for _ in range(8)]

        assert codes[0] == 201
        assert 429 in codes

    def test_reading_the_page_is_not_braked(self, page: dict[str, Any]) -> None:
        """Тормоз стоит на отправке: открыть страницу могут все сразу после концерта."""
        reader = visitor()
        codes = [reader.get(public(page["slug"])).status_code for _ in range(12)]

        assert set(codes) == {200}


class TestTheFestivalMark:
    def test_the_chosen_festival_is_offered_and_frozen_onto_the_note(self, page: dict[str, Any]) -> None:
        from apps.competitions.infrastructure.models import CompetitionModel

        festival = CompetitionModel.objects.create(
            title="Весенние голоса",
            season="2026",
            organizer_id=uuid.UUID(organization_id()),
            status="DRAFT",
        )

        offered = visitor().get(public(page["slug"])).data["data"]["festivals"]
        assert [option["title"] for option in offered] == ["Весенние голоса"]

        response = leave(visitor(), page["slug"], competitionId=str(festival.id))

        assert response.data["data"]["competitionTitle"] == "Весенние голоса"

    def test_somebody_else_s_festival_is_dropped_rather_than_recorded(self, page: dict[str, Any]) -> None:
        """Иначе по публичной ссылке можно было бы приписать отзыв чужому фестивалю."""
        from apps.competitions.infrastructure.models import CompetitionModel

        stranger = CompetitionModel.objects.create(
            title="Чужой фестиваль",
            season="2026",
            organizer_id=uuid.uuid4(),
            status="DRAFT",
        )

        response = leave(visitor(), page["slug"], competitionId=str(stranger.id))

        assert response.status_code == 201
        assert response.data["data"]["competitionId"] is None
        assert response.data["data"]["competitionTitle"] is None


class TestWhatTheOrganizerSees:
    def test_the_note_arrives_in_the_workspace(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        leave(visitor(), page["slug"], authorName="Мария")

        listed = staff_client.get("/api/v1/staff/reviews").data["data"]

        assert len(listed) == 1
        assert listed[0]["authorName"] == "Мария"
        assert staff_client.get(_PAGE).data["data"]["reviewCount"] == 1

    def test_a_deleted_note_leaves_every_list(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        review_id = leave(visitor(), page["slug"]).data["data"]["id"]

        assert staff_client.delete(f"/api/v1/staff/reviews/{review_id}").status_code == 204
        assert staff_client.get("/api/v1/staff/reviews").data["data"] == []
