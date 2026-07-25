"""Integration tests for diploma numbering (service + locked counter row).

Covers the format, the per-year series, and that the counter — not the diplomas
table — is what hands out values, so concurrent workers cannot collide.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.diplomas.application.numbering import DiplomaNumberService
from apps.diplomas.application.services import DiplomaService
from apps.diplomas.domain.diploma_number import format_diploma_number
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.models import DiplomaNumberSequenceModel, TemplateModel
from apps.diplomas.infrastructure.repositories import (
    DjangoDiplomaNumberSequence,
    DjangoDiplomaRepository,
)

pytestmark = pytest.mark.django_db

# Deliberately a different year from any competition below: the number must carry
# the *competition* year, never the creation year.
_NOW = datetime(2030, 1, 15, 12, 0, tzinfo=UTC)


def _numbers() -> DiplomaNumberService:
    return DiplomaNumberService(sequence=DjangoDiplomaNumberSequence())


def _service() -> DiplomaService:
    return DiplomaService(
        repository=DjangoDiplomaRepository(),
        snapshots=DjangoDiplomaSnapshotSource(),
        numbers=_numbers(),
    )


def _competition(*, start: date | None, season: str = "2026") -> CompetitionModel:
    return CompetitionModel.objects.create(
        title="Восходящие таланты",
        season=season,
        organizer_id=uuid.uuid4(),
        status="PUBLISHED",
        competition_start=start,
    )


def _submission(competition: CompetitionModel) -> SubmissionModel:
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": "Иванов Иван", "member_count": 1}],
        performance={"title": "Этюд"},
    )


# --- The format ------------------------------------------------------------


def test_format_is_prefix_year_and_six_digits() -> None:
    assert format_diploma_number(year=2026, sequence=1) == "VT-2026-000001"
    assert format_diploma_number(year=2026, sequence=2) == "VT-2026-000002"
    assert format_diploma_number(year=2027, sequence=123456) == "VT-2027-123456"


# --- The counter -----------------------------------------------------------


def test_counter_starts_at_one_and_increments() -> None:
    sequence = DjangoDiplomaNumberSequence()

    assert [sequence.next_value(scope="2026") for _ in range(3)] == [1, 2, 3]
    row = DiplomaNumberSequenceModel.objects.get(scope="2026")
    assert row.current_number == 3


def test_each_year_has_its_own_series() -> None:
    numbers = _numbers()

    assert numbers.next_number(competition_year=2026) == "VT-2026-000001"
    assert numbers.next_number(competition_year=2027) == "VT-2027-000001"
    assert numbers.next_number(competition_year=2026) == "VT-2026-000002"
    assert DiplomaNumberSequenceModel.objects.count() == 2


def test_counter_is_independent_of_the_diplomas_table() -> None:
    """The old ``max(number) + 1`` read the diplomas table; the counter does not.

    Deleting every diploma must not hand the same number out twice — a number is
    permanent and never reused.
    """
    from apps.diplomas.infrastructure.models import DiplomaModel

    competition = _competition(start=date(2026, 5, 15))
    template = TemplateModel.objects.create(name="Шаблон")
    service = _service()
    first = service.create_diploma(
        submission_id=_submission(competition).id, template_id=template.id, now=_NOW
    )

    DiplomaModel.objects.all().delete()
    second = service.create_diploma(
        submission_id=_submission(competition).id, template_id=template.id, now=_NOW
    )

    assert first.number == "VT-2026-000001"
    assert second.number == "VT-2026-000002"


# --- The year that goes into the number ------------------------------------


def test_number_carries_the_competition_year_not_the_system_year() -> None:
    competition = _competition(start=date(2026, 5, 15))
    template = TemplateModel.objects.create(name="Шаблон")

    diploma = _service().create_diploma(
        submission_id=_submission(competition).id, template_id=template.id, now=_NOW
    )

    # Created in 2030 (``_NOW``), but the competition is held in 2026.
    assert diploma.number == "VT-2026-000001"


def test_year_falls_back_to_the_season_when_dates_are_unset() -> None:
    competition = _competition(start=None, season="2028")
    template = TemplateModel.objects.create(name="Шаблон")

    diploma = _service().create_diploma(
        submission_id=_submission(competition).id, template_id=template.id, now=_NOW
    )

    assert diploma.number == "VT-2028-000001"


def test_year_falls_back_to_the_creation_year_without_dates_or_season() -> None:
    competition = _competition(start=None, season="сезон 2029/2030")
    template = TemplateModel.objects.create(name="Шаблон")

    diploma = _service().create_diploma(
        submission_id=_submission(competition).id, template_id=template.id, now=_NOW
    )

    assert diploma.number == "VT-2030-000001"
