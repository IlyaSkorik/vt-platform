"""Консоль оператора: все отзывы платформы в одном месте.

Единственное чтение в контексте, не ограниченное одной организацией. Оно нужно
ровно для одного: разобрать жалобу на то, что кто-то написал, — а сделать это
может только сторона, стоящая над организатором и над автором отзыва.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.composition import build_grant_platform_administrator_handler

pytestmark = pytest.mark.django_db

_PASSWORD = "V3ry$ecurePass!"
_PLATFORM_REVIEWS = "/api/v1/platform/reviews"
_CONSENT_TYPE = "review_personal_data"
_CONSENT = "1.0"


@pytest.fixture
def operator() -> APIClient:
    """A client authenticated as the platform operator (granted by command)."""
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "operator@example.com", "password": _PASSWORD, "firstName": "Илья", "lastName": "Скорик"},
        format="json",
    )
    user_id = str(registration.data["data"]["id"])
    access = str(identity_composition.build_token_service().issue(subject=user_id).access_token)
    build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user_id))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def leave(slug: str, **fields: Any) -> Any:
    payload: dict[str, Any] = {"text": "Спасибо!", "consentType": _CONSENT_TYPE, "consentVersion": _CONSENT, "consentAccepted": True}
    payload.update(fields)
    return APIClient().post(f"/api/v1/public/reviews/{slug}/entries", payload, format="multipart")


class TestTheOperatorsConsole:
    def test_every_note_is_listed_with_whose_it_is(self, operator: APIClient, page: dict[str, Any]) -> None:
        leave(page["slug"], authorName="Мария")

        response = operator.get(_PLATFORM_REVIEWS)

        assert response.status_code == 200
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["authorName"] == "Мария"
        assert response.data["data"][0]["organizationName"]

    def test_the_operator_can_remove_anybody_s_note(self, operator: APIClient, staff_client: APIClient, page: dict[str, Any]) -> None:
        """Жалоба на содержание — ровно то действие, ради которого доступ и есть."""
        review_id = leave(page["slug"]).data["data"]["id"]

        assert operator.delete(f"{_PLATFORM_REVIEWS}/{review_id}").status_code == 204
        assert operator.get(_PLATFORM_REVIEWS).data["data"] == []
        assert staff_client.get("/api/v1/staff/reviews").data["data"] == []

    def test_an_organizer_is_not_an_operator(self, staff_client: APIClient, page: dict[str, Any]) -> None:
        """Владелец организации — вершина своей организации и ничего больше."""
        assert staff_client.get(_PLATFORM_REVIEWS).status_code == 403

    def test_a_stranger_sees_nothing(self, page: dict[str, Any]) -> None:
        assert APIClient().get(_PLATFORM_REVIEWS).status_code in {401, 403}

    def test_the_module_gate_does_not_apply_to_the_operator(self, operator: APIClient, page: dict[str, Any]) -> None:
        """Отключённый организации модуль решает, что может делать она, а не оператор."""
        from apps.organization.domain.value_objects import OrganizationModule
        from tests.presentation.reviews.conftest import set_modules

        leave(page["slug"])
        set_modules(OrganizationModule.COMPETITIONS.value)

        assert len(operator.get(_PLATFORM_REVIEWS).data["data"]) == 1
