"""Unit tests for the ``Diploma`` aggregate and its snapshot value objects.

Pure domain — no Django, no database.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.value_objects import (
    AwardSnapshot,
    CompetitionSnapshot,
    DiplomaSnapshot,
    DiplomaStatus,
    NominationSnapshot,
    OrganizationSnapshot,
    ParticipantSnapshot,
    PerformanceSnapshot,
    TeacherSnapshot,
)

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


def _snapshot(*, degree: str | None = None) -> DiplomaSnapshot:
    return DiplomaSnapshot(
        participant=ParticipantSnapshot(display_name="Иванов Иван", age=12),
        teachers=(TeacherSnapshot(name="Петрова Мария", role="Педагог"),),
        organization=OrganizationSnapshot(name="ДШИ №1"),
        nomination=NominationSnapshot(title="Вокал", discipline="Эстрадный вокал"),
        performance=PerformanceSnapshot(title="Этюд"),
        competition=CompetitionSnapshot(title="Восходящие таланты", date="15.05.2026", city="Москва"),
        award=AwardSnapshot(degree=degree),
    )


def _create(snapshot: DiplomaSnapshot) -> Diploma:
    return Diploma.create(
        diploma_id=uuid.uuid4(),
        number="000001",
        verification_token="tok",
        competition_id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        template_id=uuid.uuid4(),
        snapshot=snapshot,
        now=_NOW,
    )


def test_created_diploma_is_draft_without_degree() -> None:
    diploma = _create(_snapshot(degree=None))

    assert diploma.status is DiplomaStatus.DRAFT
    assert diploma.degree is None
    assert diploma.print_pdf_path is None
    assert diploma.official_pdf_path is None
    assert diploma.issued_at is None
    assert diploma.version == 1


def test_snapshot_round_trips_through_dict() -> None:
    snapshot = _snapshot(degree="Лауреат I степени")

    restored = DiplomaSnapshot.from_dict(snapshot.to_dict())

    assert restored == snapshot


def test_award_degree_defaults_to_none() -> None:
    assert AwardSnapshot().degree is None
    assert DiplomaSnapshot.from_dict({"participant": {"display_name": "x"}}).award.degree is None


def test_with_degree_sets_only_the_degree_and_bumps_version() -> None:
    diploma = _create(_snapshot(degree=None))

    updated = diploma.with_degree("Гран-при", now=_NOW)

    assert updated.degree == "Гран-при"
    assert updated.version == 2
    # Everything else is frozen — the original is untouched.
    assert diploma.degree is None
    assert updated.number == diploma.number
    assert updated.snapshot.participant == diploma.snapshot.participant
    assert updated.snapshot.competition == diploma.snapshot.competition
