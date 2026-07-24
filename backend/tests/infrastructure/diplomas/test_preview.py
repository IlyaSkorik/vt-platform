"""Integration tests for the diploma preview BindingResolver.

Exercises the cross-context read of the Applications and Competitions contexts
against real PostgreSQL, as for every ``tests/infrastructure`` suite.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.presentation.api.v1.diplomas import preview

pytestmark = pytest.mark.django_db


def _submission(competition_id: uuid.UUID, display_name: str, **extra: object) -> SubmissionModel:
    return SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": display_name, "member_count": 1, **extra}],
        performance={"title": "Этюд"},
    )


def test_lists_applications_labelled_by_performer() -> None:
    competition_id = uuid.uuid4()
    submission = _submission(competition_id, "Иванов Иван Иванович")

    applications = preview.list_preview_applications(str(competition_id))

    assert {"id": str(submission.id), "label": "Иванов Иван Иванович"} in applications


def test_resolves_participant_display_name() -> None:
    submission = _submission(uuid.uuid4(), "Ансамбль «Созвездие»")

    bindings = preview.resolve_preview_bindings(str(submission.id))

    assert bindings is not None
    assert bindings[preview.PARTICIPANT_DISPLAY_NAME] == "Ансамбль «Созвездие»"


def test_resolves_all_catalogue_keys_with_missing_default() -> None:
    submission = _submission(uuid.uuid4(), "Иванов Иван Иванович")

    bindings = preview.resolve_preview_bindings(str(submission.id))

    assert bindings is not None
    # Every catalogue binding is present; the performance title resolves, and a
    # source not wired yet (awards) falls back to the em dash — never missing.
    assert set(bindings) == set(preview.BINDINGS)
    assert bindings[preview.PERFORMANCE_TITLE] == "Этюд"
    assert bindings[preview.AWARD_DEGREE] == preview.MISSING
    assert bindings[preview.DIPLOMA_NUMBER] == preview.MISSING


def test_resolves_participant_age_from_birth_date() -> None:
    born = date.today().replace(year=date.today().year - 12)
    submission = _submission(uuid.uuid4(), "Иванов Иван Иванович", birth_date=born.isoformat())

    bindings = preview.resolve_preview_bindings(str(submission.id))

    assert bindings is not None
    assert bindings[preview.PARTICIPANT_AGE] == "12"


def test_resolves_competition_and_nomination_across_contexts() -> None:
    competition = CompetitionModel.objects.create(
        title="Восходящие таланты",
        season="2026",
        organizer_id=uuid.uuid4(),
        status="PUBLISHED",
        venue_name="Москва",
        competition_start=date(2026, 5, 15),
    )
    category = CategoryModel.objects.create(competition=competition, name="Вокал")
    submission = SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": "Иванов Иван Иванович", "member_count": 1}],
        performance={"title": "Этюд", "nomination_id": str(category.id)},
    )

    bindings = preview.resolve_preview_bindings(str(submission.id))

    assert bindings is not None
    assert bindings[preview.COMPETITION_TITLE] == "Восходящие таланты"
    assert bindings[preview.COMPETITION_DATE] == "15.05.2026"
    assert bindings[preview.COMPETITION_CITY] == "Москва"
    assert bindings[preview.NOMINATION_TITLE] == "Вокал"


def _teacher(last: str, first: str, role: str) -> dict[str, object]:
    return {"last_name": last, "first_name": first, "middle_name": "", "role": role}


def test_teachers_with_same_role_join_on_one_line() -> None:
    submission = SubmissionModel.objects.create(
        competition_id=uuid.uuid4(),
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": "Иванов Иван", "member_count": 1}],
        teachers=[_teacher("Петрова", "Мария", "Педагог"), _teacher("Сидоров", "Пётр", "Педагог")],
    )

    bindings = preview.resolve_preview_bindings(str(submission.id))

    assert bindings is not None
    assert bindings[preview.TEACHER_DISPLAY_NAME] == "Педагог: Петрова Мария, Сидоров Пётр"


def test_teachers_with_different_roles_go_on_separate_lines() -> None:
    submission = SubmissionModel.objects.create(
        competition_id=uuid.uuid4(),
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": "Иванов Иван", "member_count": 1}],
        teachers=[
            _teacher("Петрова", "Мария", "Педагог"),
            _teacher("Сидоров", "Пётр", "Концертмейстер"),
        ],
    )

    bindings = preview.resolve_preview_bindings(str(submission.id))

    assert bindings is not None
    assert bindings[preview.TEACHER_DISPLAY_NAME] == (
        "Педагог: Петрова Мария\nКонцертмейстер: Сидоров Пётр"
    )


def test_resolve_unknown_application_returns_none() -> None:
    assert preview.resolve_preview_bindings(str(uuid.uuid4())) is None
