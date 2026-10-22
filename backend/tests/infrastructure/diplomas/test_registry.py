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
from apps.diplomas.application.numbering import DiplomaNumberService
from apps.diplomas.application.services import DiplomaService
from apps.diplomas.domain.exceptions import (
    DuplicateDiplomaError,
    SubmissionNotFoundError,
    TemplateNotFoundError,
)
from apps.diplomas.domain.value_objects import DiplomaStatus
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.models import TemplateModel
from apps.diplomas.infrastructure.repositories import (
    DjangoDiplomaNumberSequence,
    DjangoDiplomaRepository,
)

pytestmark = pytest.mark.django_db

#: One organization for everything this module builds. A template and the
#: competition it is used on have to belong to the same organizer now — the scoped
#: listings admit a row only when both sides match — so a fresh `uuid4()` per
#: competition would put them on opposite sides of the boundary.
_ORGANIZER = uuid.UUID("00000000-0000-4000-8000-0000000000a1")


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
        organizer_id=_ORGANIZER,
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
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Шаблон")

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


def test_a_diploma_names_every_participant_of_the_entry() -> None:
    # One diploma is issued per entry, so a duet's sheet has to carry both names: the
    # second performer has no document of their own to be named on.
    competition = _competition()
    category = CategoryModel.objects.create(competition=competition, name="Вокал")
    submission = SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[
            {"display_name": "Иванова Анна", "member_count": 1, "birth_date": date(2014, 1, 1).isoformat()},
            {"display_name": "Петров Пётр", "member_count": 1, "birth_date": date(2013, 6, 1).isoformat()},
        ],
        performance={"title": "Дуэт", "nomination_id": str(category.id)},
    )
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Шаблон")

    diploma = _service().create_diploma(submission_id=submission.id, template_id=template.id, now=_NOW)

    assert diploma.snapshot.participant.display_name == "Иванова Анна, Петров Пётр"


def test_numbers_are_unique_and_sequential() -> None:
    competition = _competition()
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Шаблон")
    service = _service()

    first = service.create_diploma(submission_id=_submission(competition).id, template_id=template.id, now=_NOW)
    second = service.create_diploma(submission_id=_submission(competition).id, template_id=template.id, now=_NOW)

    # VT-<competition year>-<six digits>, consecutive within the year.
    assert first.number == "VT-2026-000001"
    assert second.number == "VT-2026-000002"
    assert first.verification_token != second.verification_token


def test_registry_lists_competition_diplomas_and_reads_one() -> None:
    competition = _competition()
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Шаблон")
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


def test_one_diploma_per_performance() -> None:
    competition = _competition()
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Шаблон")
    submission = _submission(competition)
    service = _service()
    service.create_diploma(submission_id=submission.id, template_id=template.id, now=_NOW)

    # A submission is exactly one performance — a second diploma is rejected.
    with pytest.raises(DuplicateDiplomaError):
        service.create_diploma(submission_id=submission.id, template_id=template.id, now=_NOW)


def test_unknown_submission_raises() -> None:
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Шаблон")

    with pytest.raises(SubmissionNotFoundError):
        _service().create_diploma(submission_id=uuid.uuid4(), template_id=template.id, now=_NOW)
