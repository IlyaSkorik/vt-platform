"""Integration tests for the public Registration read projection.

``GET /api/v1/public/competitions/{id}/registration`` — the single, unauthenticated
projection the Registration Wizard consumes. Exercised end to end against real
PostgreSQL: a seeded competition is projected through the Competition aggregate.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.competitions.infrastructure.models.base import uuid7

pytestmark = pytest.mark.django_db


def _seed_competition(*, status: str = "PUBLISHED", open_nomination: bool = True) -> str:
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status=status, title="Spring Festival", season="2025/2026")
    if open_nomination:
        # Registration is scheduled per nomination; an open window makes the competition
        # accept applications (its top-level registrationOpen becomes true).
        CategoryModel.objects.create(
            competition=competition,
            name="Vocal",
            registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
            registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
        )
    return str(competition.id)


def _url(competition_id: str) -> str:
    return f"/api/v1/public/competitions/{competition_id}/registration"


def test_returns_single_projection_for_open_competition() -> None:
    competition_id = _seed_competition()
    response = APIClient().get(_url(competition_id))
    assert response.status_code == 200, response.data
    data = response.data["data"]
    assert data["competition"]["id"] == competition_id
    assert data["competition"]["title"] == "Spring Festival"
    assert data["registrationOpen"] is True
    # The open nomination is projected with its per-nomination registration state.
    assert len(data["nominations"]) == 1
    nomination = data["nominations"][0]
    assert nomination["registrationOpen"] is True
    assert nomination["registrationStopped"] is False
    assert nomination["registrationOpensAt"] is not None
    assert nomination["registrationClosesAt"] is not None
    # Every config axis the wizard needs is present as a (possibly empty) list.
    for key in (
        "nominations",
        "disciplines",
        "ageCategories",
        "participantGroups",
        "participationFormats",
        "admissionRules",
        "additionalServices",
        "requiredConsents",
        "uploadRequirements",
    ):
        assert key in data
        assert isinstance(data[key], list)
    # Two consents are the platform's, not the organizer's: a child's data is held on
    # the representative's consent and results are published on consent to
    # distribution, so neither is a setting a festival can switch off
    # (LEGAL-001 §4.1, §8.3).
    codes = {consent["code"]: consent["required"] for consent in data["requiredConsents"]}
    assert codes["personal_data"] is True
    assert codes["distribution"] is True
    # The festival decides on these.
    assert "media" in codes
    assert "regulations" in codes
    # Offered always, required never: withholding it only means the work is not
    # published in the open sections (LEGAL-001 §8.5).
    assert codes["work_publication"] is False


def test_unauthenticated_access_is_allowed() -> None:
    competition_id = _seed_competition()
    # No Authorization header at all.
    assert APIClient().get(_url(competition_id)).status_code == 200


def test_unknown_competition_is_404_problem() -> None:
    response = APIClient().get(_url(str(uuid7())))
    assert response.status_code == 404
    assert response["Content-Type"] == "application/problem+json"


def test_malformed_id_is_404_not_500() -> None:
    assert APIClient().get(_url("not-a-uuid")).status_code == 404


def test_draft_competition_is_hidden() -> None:
    competition_id = _seed_competition(status="DRAFT")
    assert APIClient().get(_url(competition_id)).status_code == 404


def test_v4_uuid_is_hidden() -> None:
    # A well-formed but non-v7 id never matches a real competition id.
    assert APIClient().get(_url(str(uuid.uuid4()))).status_code == 404


def test_upload_requirements_carry_the_video_limits() -> None:
    # An in-person festival collects the file for the hall's screen, so the wizard needs
    # the same two facts for video it already has for music: which extensions and how
    # large. Sent whatever the mode is, so the client never invents a limit of its own
    # that the server would then enforce differently.
    competition_id = _seed_competition()
    data = APIClient().get(_url(competition_id)).data["data"]

    for requirement in data["uploadRequirements"]:
        assert isinstance(requirement["videoAllowedFormats"], list)
        assert requirement["videoAllowedFormats"]
        assert requirement["videoMaxUploadSizeMb"] >= 1
