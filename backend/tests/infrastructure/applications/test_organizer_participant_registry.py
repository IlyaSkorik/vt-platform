"""Projection tests for the organizer Participant Registry read model.

Exercises the real Django adapter against PostgreSQL: participants are derived
from submission rows, grouped across submissions by ``registry_participant_id``,
restricted to confirmed lifecycle states, and — the confidentiality invariant —
never surfaced from competitions outside the requested scope.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest

from apps.applications.application.read_models import RegistryFilters
from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.applications.infrastructure.read_models import DjangoOrganizerParticipantRegistry
from apps.participants.infrastructure.models import (
    EducationalOrganizationModel,
    ParticipantOrganizationMembershipModel,
    ParticipantRegistryModel,
)

pytestmark = pytest.mark.django_db

COMP_A = str(uuid.uuid4())
COMP_B = str(uuid.uuid4())
COMP_OTHER = str(uuid.uuid4())
REGISTRY_P1 = str(uuid.uuid4())
REGISTRY_P2 = str(uuid.uuid4())


def _participant(registry_id: str, *, first: str, last: str, birth: str, gender: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "display_name": f"{last} {first}",
        "first_name": first,
        "last_name": last,
        "middle_name": None,
        "birth_date": birth,
        "gender": gender,
        "registry_participant_id": registry_id,
        "member_count": 1,
    }


def _make_submission(
    *,
    competition_id: str,
    status: str,
    participants: list[dict[str, Any]],
    teachers: list[dict[str, Any]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    notes: list[dict[str, Any]] | None = None,
    comment: str | None = None,
    updated: datetime,
) -> SubmissionModel:
    return SubmissionModel.objects.create(
        competition_id=competition_id,
        applicant_id=uuid.uuid4(),
        status=status,
        performance={
            "title": "Танец",
            "duration_seconds": 180,
            "nomination_id": str(uuid.uuid4()),
            "discipline_id": str(uuid.uuid4()),
            "age_category_id": str(uuid.uuid4()),
            "participant_group_id": str(uuid.uuid4()),
            "participation_format_id": str(uuid.uuid4()),
            # Omitted entirely when unset, mirroring rows written before the field existed.
            **({} if comment is None else {"comment": comment}),
        },
        participants=participants,
        teachers=teachers or [],
        attachments=attachments or [],
        organizer_notes=notes or [],
        created_at=updated,
        updated_at=updated,
    )


@pytest.fixture
def registry() -> DjangoOrganizerParticipantRegistry:
    return DjangoOrganizerParticipantRegistry()


@pytest.fixture
def _seed() -> None:
    teacher = {"first_name": "Мария", "last_name": "Иванова", "middle_name": None, "role": "COACH"}
    # Two confirmed submissions for the same child (P1) in competition A.
    s1 = _make_submission(
        competition_id=COMP_A,
        status="ACCEPTED",
        participants=[_participant(REGISTRY_P1, first="Пётр", last="Петров", birth="2015-05-01", gender="male")],
        teachers=[teacher],
        attachments=[{"id": str(uuid.uuid4()), "type": "DOCUMENT", "file": "ref://doc1", "caption": "Согласие"}],
        notes=[{"text": "Проверить документы", "created_by": "org", "created_at": "2026-07-10T10:00:00Z"}],
        updated=datetime(2026, 7, 10, 10, 0, tzinfo=UTC),
    )
    s2 = _make_submission(
        competition_id=COMP_A,
        status="PAID",
        participants=[_participant(REGISTRY_P1, first="Пётр", last="Петров", birth="2015-05-01", gender="male")],
        teachers=[teacher],
        updated=datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
    )
    # A DRAFT for the same child — must be excluded (not a confirmed participant).
    _make_submission(
        competition_id=COMP_A,
        status="DRAFT",
        participants=[_participant(REGISTRY_P1, first="Пётр", last="Петров", birth="2015-05-01", gender="male")],
        updated=datetime(2026, 7, 13, 10, 0, tzinfo=UTC),
    )
    # A different child (P2) in competition B.
    _make_submission(
        competition_id=COMP_B,
        status="COMPLETED",
        participants=[_participant(REGISTRY_P2, first="Анна", last="Сидорова", birth="2014-03-03", gender="female")],
        updated=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
    )
    # The SAME child (P1) in an out-of-scope competition — the confidentiality case.
    _make_submission(
        competition_id=COMP_OTHER,
        status="ACCEPTED",
        participants=[_participant(REGISTRY_P1, first="Пётр", last="Петров", birth="2015-05-01", gender="male")],
        updated=datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
    )
    # Applications link submissions to their order id (used for deep links).
    for submission in (s1, s2):
        ApplicationModel.objects.create(
            competition_id=COMP_A,
            applicant_id=submission.applicant_id,
            status="PAID",
            submission_refs=[{"submission_id": str(submission.id)}],
        )
    # A participant's educational organization lives in the Participants registry,
    # linked by the registry_participant_id the submission denormalizes.
    org = EducationalOrganizationModel.objects.create(owner_id=uuid.uuid4(), name="Школа №1", organization_type="school")
    registry = ParticipantRegistryModel.objects.create(
        id=uuid.UUID(REGISTRY_P1),
        owner_id=uuid.uuid4(),
        first_name="Пётр",
        last_name="Петров",
        birth_date=date(2015, 5, 1),
        gender="male",
    )
    ParticipantOrganizationMembershipModel.objects.create(participant=registry, organization=org, is_primary=True)


SCOPE = (COMP_A, COMP_B)


def test_projection_groups_confirmed_submissions_per_child(registry: DjangoOrganizerParticipantRegistry, _seed: None) -> None:
    rows = registry.list(competition_ids=SCOPE, filters=RegistryFilters())
    by_name = {row.full_name: row for row in rows}
    assert set(by_name) == {"Петров Пётр", "Сидорова Анна"}

    petrov = by_name["Петров Пётр"]
    # Two confirmed submissions grouped into one entry; the DRAFT is excluded.
    assert petrov.applications_count == 2
    assert petrov.competitions_count == 1
    assert petrov.age == 11  # born 2015-05-01; birthday already passed by 2026-07-20
    assert petrov.gender == "male"
    assert petrov.primary_organization is not None
    assert petrov.primary_organization.name == "Школа №1"
    assert [t.name for t in petrov.teachers] == ["Иванова Мария"]  # deduped across submissions
    assert petrov.documents_count == 1


def test_scope_excludes_out_of_scope_and_other_competitions(registry: DjangoOrganizerParticipantRegistry, _seed: None) -> None:
    # Confidentiality: the child's participation in COMP_OTHER never surfaces,
    # even though it is a confirmed submission for the same registry id.
    petrov = next(r for r in registry.list(competition_ids=SCOPE, filters=RegistryFilters()) if r.last_name == "Петров")
    assert petrov.competitions_count == 1  # only COMP_A, not COMP_OTHER

    only_b = registry.list(competition_ids=[COMP_B], filters=RegistryFilters())
    assert [r.last_name for r in only_b] == ["Сидорова"]


def test_competition_filter_narrows_list(registry: DjangoOrganizerParticipantRegistry, _seed: None) -> None:
    rows = registry.list(competition_ids=SCOPE, filters=RegistryFilters(competition_id=COMP_B))
    assert {r.last_name for r in rows} == {"Сидорова"}


def test_query_and_gender_filters(registry: DjangoOrganizerParticipantRegistry, _seed: None) -> None:
    assert {r.last_name for r in registry.list(competition_ids=SCOPE, filters=RegistryFilters(query="сидор"))} == {"Сидорова"}
    assert {r.last_name for r in registry.list(competition_ids=SCOPE, filters=RegistryFilters(gender="male"))} == {"Петров"}


def test_detail_returns_full_card_across_scope(registry: DjangoOrganizerParticipantRegistry, _seed: None) -> None:
    petrov = next(r for r in registry.list(competition_ids=SCOPE, filters=RegistryFilters()) if r.last_name == "Петров")
    detail = registry.get(competition_ids=SCOPE, key=petrov.key)
    assert detail is not None
    assert len(detail.applications) == 2
    assert len(detail.notes) == 1
    assert detail.notes[0].text == "Проверить документы"
    assert detail.awards == ()  # no results/judging source yet
    assert len(detail.history) == 2


def test_detail_surfaces_the_performance_comment_when_the_applicant_left_one(registry: DjangoOrganizerParticipantRegistry) -> None:
    """The organizer's participant card carries the note; rows without one stay None."""
    _make_submission(
        competition_id=COMP_A,
        status="ACCEPTED",
        participants=[_participant(REGISTRY_P1, first="Пётр", last="Петров", birth="2015-05-01", gender="male")],
        comment="  Выход с точки 3.  ",
        updated=datetime(2026, 7, 10, 10, 0, tzinfo=UTC),
    )
    _make_submission(
        competition_id=COMP_A,
        status="ACCEPTED",
        participants=[_participant(REGISTRY_P2, first="Анна", last="Сидорова", birth="2014-03-03", gender="female")],
        updated=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
    )

    rows = registry.list(competition_ids=SCOPE, filters=RegistryFilters())
    comments = {}
    for row in rows:
        detail = registry.get(competition_ids=SCOPE, key=row.key)
        assert detail is not None
        comments[row.last_name] = [performance.comment for performance in detail.performances]

    assert comments["Петров"] == ["Выход с точки 3."]
    assert comments["Сидорова"] == [None]


def test_detail_missing_key_returns_none(registry: DjangoOrganizerParticipantRegistry, _seed: None) -> None:
    assert registry.get(competition_ids=SCOPE, key="r:does-not-exist") is None
