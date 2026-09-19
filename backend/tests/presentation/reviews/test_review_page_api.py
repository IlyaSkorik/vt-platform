"""Страница отзывов в кабинете организатора.

Организатор печатает QR на баннере, и это решает всё остальное: ссылка должна
появиться один раз и больше не меняться, страница — открываться и закрываться без
замены баннера, а чужие отзывы не должны быть ни видны, ни удаляемы.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.organization.domain.value_objects import OrganizationModule
from tests.presentation.reviews.conftest import set_modules

pytestmark = pytest.mark.django_db

_PAGE = "/api/v1/staff/reviews/page"
_REVIEWS = "/api/v1/staff/reviews"


class TestThePage:
    def test_the_first_read_mints_it(self, page: dict[str, Any]) -> None:
        assert page["slug"]
        assert page["accepting"] is True
        assert page["reviewCount"] == 0

    def test_the_link_never_changes(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        """Баннер напечатан один раз; вторая ссылка означала бы вторую печать."""
        again = staff_client.get(_PAGE)

        assert again.data["data"]["slug"] == page["slug"]
        assert again.data["data"]["id"] == page["id"]

    def test_the_organizer_rewrites_the_wording(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        response = staff_client.patch(_PAGE, {"title": "Как вам фестиваль?", "intro": "Нам важно ваше мнение."}, format="json")

        assert response.status_code == 200, response.data
        assert response.data["data"]["title"] == "Как вам фестиваль?"
        assert response.data["data"]["intro"] == "Нам важно ваше мнение."
        assert response.data["data"]["slug"] == page["slug"]

    def test_closing_and_reopening_leaves_the_link_alone(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        closed = staff_client.patch(_PAGE, {"accepting": False}, format="json")
        assert closed.data["data"]["accepting"] is False
        assert closed.data["data"]["slug"] == page["slug"]

        reopened = staff_client.patch(_PAGE, {"accepting": True}, format="json")
        assert reopened.data["data"]["accepting"] is True

    def test_switching_the_page_off_does_not_erase_its_wording(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        """Переключатель и форма текста — два разных элемента одного экрана."""
        staff_client.patch(_PAGE, {"title": "Как вам фестиваль?"}, format="json")

        closed = staff_client.patch(_PAGE, {"accepting": False}, format="json")

        assert closed.data["data"]["title"] == "Как вам фестиваль?"

    def test_the_qr_is_a_png(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        response = staff_client.get(f"{_PAGE}/qr.png")

        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"
        assert page["slug"] in response["Content-Disposition"]


class TestTheModuleGate:
    def test_an_organization_without_the_module_is_refused(self, staff_client: APIClient) -> None:
        """Не проданный блок закрыт, а не просто спрятан из меню."""
        set_modules(OrganizationModule.COMPETITIONS.value)

        assert staff_client.get(_PAGE).status_code == 403
        assert staff_client.get(_REVIEWS).status_code == 403

    def test_a_stranger_without_an_account_is_refused(self) -> None:
        assert APIClient().get(_PAGE).status_code in {401, 403}


class TestTheList:
    def test_an_untouched_page_has_nothing_on_it(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        response = staff_client.get(_REVIEWS)

        assert response.status_code == 200
        assert response.data["data"] == []

    def test_a_review_that_is_not_ours_cannot_be_deleted(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        """Чужой отзыв отвечает «не найдено»: даже подтверждение, что id существует,
        уже рассказывает одной организации о другой."""
        from apps.reviews.infrastructure.models import ReviewModel, ReviewPageModel, uuid7

        other_organization = uuid7()
        other_page = ReviewPageModel.objects.create(organization_id=other_organization, slug="ZZZZZZZZZZ", title="Чужая страница")
        stranger = ReviewModel.objects.create(
            page=other_page,
            organization_id=other_organization,
            text="Чужой отзыв",
            consent_code="review_personal_data",
            consent_version="1.0",
            consent_accepted_at="2026-09-19T10:00:00Z",
            submitted_at="2026-09-19T10:00:00Z",
        )

        response = staff_client.delete(f"{_REVIEWS}/{stranger.id}")

        assert response.status_code == 404
        assert ReviewModel.objects.filter(pk=stranger.id, deleted_at__isnull=True).exists()

    def test_a_malformed_id_answers_the_same_as_a_stranger_s(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        assert staff_client.delete(f"{_REVIEWS}/not-a-uuid").status_code == 404
