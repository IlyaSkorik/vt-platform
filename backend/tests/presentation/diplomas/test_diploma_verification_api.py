"""Integration tests for the public diploma verification endpoint (QR target).

Driven through DRF's ``APIClient`` with **no** authentication — this is the only
unauthenticated diploma endpoint. Each case runs end to end: a real diploma is
created through :class:`DiplomaService` (so the snapshot under test is the one the
write path actually froze), then read back through
``GET /api/v1/public/diplomas/verify/{token}`` → reader → serializer →
``{data, meta}`` envelope / RFC 9457 problem.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.application.numbering import DiplomaNumberService
from apps.diplomas.application.services import DiplomaService
from apps.diplomas.domain.entities import Diploma
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.models import DiplomaModel, TemplateModel
from apps.diplomas.infrastructure.repositories import (
    DjangoDiplomaNumberSequence,
    DjangoDiplomaRepository,
)

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


def _service() -> DiplomaService:
    return DiplomaService(
        repository=DjangoDiplomaRepository(),
        snapshots=DjangoDiplomaSnapshotSource(),
        numbers=DiplomaNumberService(sequence=DjangoDiplomaNumberSequence()),
    )


def _competition() -> CompetitionModel:
    return CompetitionModel.objects.create(
        title="Восходящие таланты",
        season="2026",
        organizer_id=uuid.uuid4(),
        status="PUBLISHED",
        venue_name="Москва",
        competition_start=date(2026, 5, 15),
    )


def _submission(competition: CompetitionModel, *, category: CategoryModel | None = None) -> SubmissionModel:
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[
            {"display_name": "Иванов Иван", "member_count": 1, "birth_date": date(2014, 1, 1).isoformat()}
        ],
        teachers=[{"first_name": "Мария", "last_name": "Петрова", "middle_name": "", "role": "Педагог"}],
        performance={"title": "Этюд", "nomination_id": str(category.id) if category else ""},
    )


def _diploma() -> Diploma:
    """One real diploma, created the way the organizer workspace creates it."""
    competition = _competition()
    category = CategoryModel.objects.create(competition=competition, name="Вокал")
    submission = _submission(competition, category=category)
    template = TemplateModel.objects.create(name="Шаблон")
    return _service().create_diploma(submission_id=submission.id, template_id=template.id, now=_NOW)


def _verify(token: str):
    return APIClient().get(f"/api/v1/public/diplomas/verify/{token}")


class TestSuccessfulVerification:
    def test_returns_the_snapshotted_facts_without_authentication(self) -> None:
        diploma = _diploma()

        response = _verify(diploma.verification_token)

        assert response.status_code == 200
        data = response.data["data"]
        assert data["verified"] is True
        assert data["number"] == "VT-2026-000001"
        assert data["participantName"] == "Иванов Иван"
        assert data["competitionTitle"] == "Восходящие таланты"
        assert data["nomination"] == "Вокал"
        assert data["performance"] == "Этюд"
        assert data["teacher"] == "Петрова Мария"
        assert response["X-Request-ID"]

    def test_snapshot_is_the_source_so_later_edits_never_change_the_page(self) -> None:
        diploma = _diploma()
        # Rename the participant on the submission the diploma was built from.
        submission = SubmissionModel.objects.get(id=diploma.submission_id)
        submission.participants = [{"display_name": "Кто-то Другой", "member_count": 1}]
        submission.save(update_fields=["participants"])

        response = _verify(diploma.verification_token)

        # The frozen snapshot still governs — the page cannot drift from the paper.
        assert response.data["data"]["participantName"] == "Иванов Иван"


class TestUnknownToken:
    def test_unknown_token_is_a_404_problem(self) -> None:
        _diploma()

        response = _verify("definitely-not-a-real-token")

        assert response.status_code == 404
        assert response["Content-Type"].startswith("application/problem+json")
        assert response.data["title"] == "Resource not found"
        assert response.data["status"] == 404

    def test_a_revoked_diploma_stops_verifying(self) -> None:
        diploma = _diploma()
        DiplomaModel.objects.filter(id=diploma.id).update(deleted_at=_NOW)

        response = _verify(diploma.verification_token)

        # Indistinguishable from an unknown token — its former existence is not leaked.
        assert response.status_code == 404


class TestPendingDegree:
    def test_degree_is_null_until_the_jury_has_sat(self) -> None:
        diploma = _diploma()
        assert diploma.degree is None

        response = _verify(diploma.verification_token)

        # Null, not "не указано": the client renders "результаты ещё не опубликованы".
        assert response.data["data"]["degree"] is None

    def test_degree_appears_once_assigned(self) -> None:
        diploma = _diploma()
        DjangoDiplomaRepository().update(diploma.with_degree("Лауреат I степени", now=_NOW))

        response = _verify(diploma.verification_token)

        assert response.data["data"]["degree"] == "Лауреат I степени"


class TestOfficialPdf:
    def test_no_pdf_url_while_the_official_pdf_is_unrendered(self) -> None:
        diploma = _diploma()

        response = _verify(diploma.verification_token)

        # Null ⇒ the page shows no download button at all.
        assert response.data["data"]["officialPdfUrl"] is None

    def test_pdf_url_appears_as_soon_as_the_file_exists(self) -> None:
        diploma = _diploma()
        path = f"/media/diplomas/official/{diploma.competition_id}/{diploma.number}.pdf"
        DiplomaModel.objects.filter(id=diploma.id).update(official_pdf_path=path)

        response = _verify(diploma.verification_token)

        # Nothing else had to change for the button to appear.
        assert response.data["data"]["officialPdfUrl"] == path
