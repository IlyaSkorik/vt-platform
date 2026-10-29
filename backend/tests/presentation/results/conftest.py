"""Общие фикстуры для REST-наборов контекста Results."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.identity.presentation.api.v1.auth import composition as identity_composition
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.composition import build_provision_owner_handler

_PASSWORD = "V3ry$ecurePass!"


@pytest.fixture
def staff_client() -> APIClient:
    """APIClient, под которым сидит владелец организации."""
    client = APIClient()
    registration = client.post(
        "/api/v1/auth/registration",
        {"email": "owner@example.com", "password": _PASSWORD, "firstName": "Org", "lastName": "Owner"},
        format="json",
    )
    access = str(identity_composition.build_token_service().issue(subject=registration.data["data"]["id"]).access_token)
    user_id = str(AccessToken(access)["user_id"])  # type: ignore[arg-type]
    build_provision_owner_handler().handle(ProvisionOwnerCommand(user_id=user_id))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def competition(staff_client: APIClient) -> dict[str, Any]:
    """Фестиваль с одной номинацией — ровно столько, сколько нужно протоколу."""
    created = staff_client.post("/api/v1/competitions", {"title": "Весна талантов", "season": "2026"}, format="json")
    assert created.status_code == 201, created.data
    competition_id = created.data["data"]["id"]
    category = staff_client.post(f"/api/v1/competitions/{competition_id}/categories", {"name": "Вокал"}, format="json")
    assert category.status_code in {200, 201}, category.data
    detail: dict[str, Any] = staff_client.get(f"/api/v1/competitions/{competition_id}").data["data"]
    return detail


def seed_act(competition_id: str, category_id: str, title: str) -> str:
    """Одна принятая заявка в той форме, в какой её хранит контекст заявок."""
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
