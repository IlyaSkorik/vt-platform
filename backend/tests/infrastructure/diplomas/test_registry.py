"""Integration tests for the diploma registry (service + repository + snapshot).

Exercises the cross-context snapshot build and the persistence round-trip.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.application.services import DiplomaService
from apps.diplomas.domain.exceptions import SubmissionNotFoundError, TemplateNotFoundError
from apps.diplomas.domain.value_objects import DiplomaStatus
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.models import TemplateModel
from apps.diplomas.infrastructure.repositories import DjangoDiplomaRepository

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


def _service() -> DiplomaService:
    return DiplomaService(repository=DjangoDiplomaRepository(), snapshots=DjangoDiplomaSnapshotSource())


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
    born = date(2014, 1, 1)
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": "Иванов Иван", "member_count": 1, "birth_date": born.isoformat()}],
        teachers=[{"first_name": "Мария", "last_name": "Петрова", "middle_name": "", "role": "Педагог"}],
        performance={"title": "Этюд", "nomination_id": str(category.id) if category else ""},
    )


def test_create_diploma_snapshots_and_starts_draft_without_degree() -> None:
    competition = _competition()
    category = CategoryModel.objects.create(competition=competition, name="Вокал")
    submission = _submission(competition, category=category)
    template = TemplateModel.objects.create(name="Шаблон")

    diploma = _service().create_diploma(submission_id=submission.id, template_id=template.id, now=_NOW)

    assert diploma.status is DiplomaStatus.DRAFT
    assert diploma.degree is None
    assert diploma.number
    assert diploma.verification_token
    assert diploma.competition_id == competition.id
    assert diploma.snapshot.participant.display_name == "Иванов Иван"
    assert diploma.snapshot.participant.age is not None
    assert diploma.snapshot.nomination.title == "Вокал"
    assert diploma.snapshot.competition.title == "Восходящие таланты"
    assert diploma.snapshot.competition.city == "Москва"
    assert diploma.snapshot.teachers[0].name == "Петрова Мария"


def test_numbers_are_unique_and_sequential() -> None:
    competition = _competition()
    template = TemplateModel.objects.create(name="Шаблон")
    service = _service()

    first = service.create_diploma(submission_id=_submission(competition).id, template_id=template.id, now=_NOW)
    second = service.create_diploma(submission_id=_submission(competition).id, template_id=template.id, now=_NOW)

    assert first.number != second.number
    assert int(second.number) == int(first.number) + 1
    assert first.verification_token != second.verification_token


def test_registry_lists_competition_diplomas_and_reads_one() -> None:
    competition = _competition()
    template = TemplateModel.objects.create(name="Шаблон")
    service = _service()
    created = service.create_diploma(submission_id=_submission(competition).id, template_id=template.id, now=_NOW)

    listed = service.list_for_competition(competition.id)
    fetched = service.get_diploma(created.id)

    assert [d.id for d in listed] == [created.id]
    assert fetched.number == created.number
    # The snapshot survives a persistence round-trip.
    assert fetched.snapshot == created.snapshot


def test_unknown_template_raises() -> None:
    competition = _competition()
    submission = _submission(competition)

    with pytest.raises(TemplateNotFoundError):
        _service().create_diploma(submission_id=submission.id, template_id=uuid.uuid4(), now=_NOW)


def test_unknown_submission_raises() -> None:
    template = TemplateModel.objects.create(name="Шаблон")

    with pytest.raises(SubmissionNotFoundError):
        _service().create_diploma(submission_id=uuid.uuid4(), template_id=template.id, now=_NOW)
