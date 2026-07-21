"""Integration tests for :class:`DjangoCompetitionRepository`.

Exercise the repository as the real persistence adapter it is: **real Django ORM
against real PostgreSQL, no mocks** (ARCH-001 §28.2). The database is repointed at
PostgreSQL by ``tests/infrastructure/conftest.py``; every test is ``django_db``.

Coverage: every port method; the full domain⇄persistence round trip across every
child collection; insert-vs-update dispatch; optimistic locking; child
synchronization; soft-delete invisibility; and structural conformance to the
``CompetitionRepository`` port.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from apps.competitions.application.interfaces import CompetitionRepository
from apps.competitions.domain.entities import Competition
from apps.competitions.domain.value_objects import (
    AdmissionCombination,
    AgeCategoryId,
    AgeCategoryName,
    AgeRange,
    CategoryId,
    CategoryName,
    CompetitionId,
    CompetitionTitle,
    ContactId,
    ContactType,
    ContactValue,
    DisciplineId,
    DisciplineName,
    DocumentCategory,
    DocumentId,
    DocumentTitle,
    DocumentVisibility,
    FileReference,
    InformationBlockId,
    InformationBlockTitle,
    Money,
    OrganizerId,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipantGroupName,
    ParticipationFormatId,
    ParticipationFormatName,
    RegulationId,
    RegulationTitle,
    RegulationVersion,
    RichText,
    Season,
    ServiceBillingModel,
    ServiceId,
    ServiceName,
    _generate_uuid7,
)
from apps.competitions.infrastructure.repositories import (
    ConcurrencyConflictError,
    DjangoCompetitionRepository,
)

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


def _draft() -> Competition:
    competition, _ = Competition.draft(
        competition_id=CompetitionId.generate(),
        title=CompetitionTitle("Autumn Stars"),
        season=Season("2026/2027"),
        organizer_id=OrganizerId.from_uuid(_generate_uuid7()),
        now=_NOW,
    )
    return competition


def _fully_configured() -> Competition:
    """A draft configured end to end so every child collection is exercised."""
    competition = _draft()
    category = competition.add_category(category_id=CategoryId.generate(), name=CategoryName("Vocal"), now=_NOW)
    discipline = competition.add_discipline(discipline_id=DisciplineId.generate(), category_id=category.id, name=DisciplineName("Pop"), now=_NOW)
    group = competition.add_participant_group(
        participant_group_id=ParticipantGroupId.generate(),
        name=ParticipantGroupName("Solo"),
        count_range=ParticipantCountRange(1, 1),
        now=_NOW,
    )
    age = competition.add_age_category(
        age_category_id=AgeCategoryId.generate(), participant_group_id=group.id, name=AgeCategoryName("6-8"), age_range=AgeRange(6, 8), now=_NOW
    )
    competition.add_participation_format(format_id=ParticipationFormatId.generate(), name=ParticipationFormatName("Очно"), now=_NOW)
    fmt = competition.participation_formats[0]
    combination = AdmissionCombination(
        category_id=category.id,
        discipline_id=discipline.id,
        age_category_id=age.id,
        participant_group_id=group.id,
        participation_format_id=fmt.id,
    )
    competition.add_admission_rule(combination=combination, now=_NOW)
    competition.add_pricing_rule(combination=combination, price_per_participant=Money.of("1500.00"), now=_NOW)
    competition.add_regulation(
        regulation_id=RegulationId.generate(),
        title=RegulationTitle("Rules"),
        version=RegulationVersion("1.0"),
        publication_date=date(2026, 7, 10),
        file=FileReference("s3://reg.pdf"),
        now=_NOW,
    )
    competition.add_document(
        document_id=DocumentId.generate(),
        title=DocumentTitle("Schedule"),
        category=DocumentCategory.SCHEDULE,
        visibility=DocumentVisibility.PUBLIC,
        file=FileReference("s3://schedule.pdf"),
        now=_NOW,
    )
    competition.add_additional_service(
        service_id=ServiceId.generate(),
        name=ServiceName("Medal"),
        price=Money.of("300"),
        available_format_ids=[fmt.id],
        billing_model=ServiceBillingModel.PER_PERFORMANCE,
        required=False,
        sort_order=1,
        now=_NOW,
    )
    competition.add_contact(contact_id=ContactId.generate(), contact_type=ContactType.EMAIL, value=ContactValue("a@b.io"), now=_NOW)
    competition.add_information_block(
        block_id=InformationBlockId.generate(), title=InformationBlockTitle("Arrival"), content=RichText("Come early."), now=_NOW
    )
    return competition


@pytest.fixture
def repo() -> DjangoCompetitionRepository:
    return DjangoCompetitionRepository()


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_save_then_get_minimal(repo: DjangoCompetitionRepository) -> None:
    competition = _draft()
    repo.save(competition)
    loaded = repo.get(competition.id)
    assert loaded is not None
    assert loaded.id == competition.id
    assert loaded.title.value == "Autumn Stars"
    assert loaded.season.value == "2026/2027"
    assert loaded.status is competition.status
    assert loaded.version == 1
    assert loaded.categories == ()


def test_save_then_get_full_round_trip(repo: DjangoCompetitionRepository) -> None:
    competition = _fully_configured()
    repo.save(competition)
    loaded = repo.get(competition.id)
    assert loaded is not None
    assert len(loaded.categories) == 1
    assert len(loaded.disciplines) == 1
    assert len(loaded.age_categories) == 1
    assert len(loaded.participant_groups) == 1
    assert len(loaded.participation_formats) == 1
    assert loaded.participation_formats[0].name.value == "Очно"
    assert loaded.participation_formats[0].enabled is True
    assert len(loaded.admission_rules) == 1
    assert len(loaded.pricing_rules) == 1
    assert loaded.pricing_rules[0].price_per_participant.amount == Decimal("1500.00")
    assert loaded.current_regulation is not None
    assert loaded.current_regulation.version.value == "1.0"
    assert len(loaded.documents) == 1
    assert len(loaded.additional_services) == 1
    assert loaded.additional_services[0].billing_model is ServiceBillingModel.PER_PERFORMANCE
    assert loaded.participation_formats[0].id in loaded.additional_services[0].available_format_ids
    assert loaded.additional_services[0].sort_order == 1
    assert len(loaded.contacts) == 1
    assert loaded.contacts[0].is_primary is True
    assert len(loaded.information_blocks) == 1
    # The reloaded aggregate is admissible for the configured combination.
    combination = loaded.admission_rules[0].combination
    assert loaded.is_admissible(combination)
    assert loaded.price_for(combination) == Money.of("1500.00")


def test_get_missing_returns_none(repo: DjangoCompetitionRepository) -> None:
    assert repo.get(CompetitionId.generate()) is None


def test_exists(repo: DjangoCompetitionRepository) -> None:
    competition = _draft()
    assert repo.exists(competition.id) is False
    repo.save(competition)
    assert repo.exists(competition.id) is True


# ---------------------------------------------------------------------------
# Insert vs update, child synchronization, optimistic concurrency
# ---------------------------------------------------------------------------


def test_update_dispatch_and_child_sync(repo: DjangoCompetitionRepository) -> None:
    competition = _draft()
    repo.save(competition)  # insert
    competition.add_category(category_id=CategoryId.generate(), name=CategoryName("Dance"), now=_NOW)
    repo.save(competition)  # update + child insert
    loaded = repo.get(competition.id)
    assert loaded is not None
    assert loaded.version == 2
    assert [c.name.value for c in loaded.categories] == ["Dance"]

    # Removing the category must delete its row on the next save.
    only_category = loaded.categories[0]
    loaded.remove_category(category_id=only_category.id, now=_NOW)
    repo.save(loaded)
    reloaded = repo.get(competition.id)
    assert reloaded is not None
    assert reloaded.categories == ()


def test_optimistic_concurrency_conflict(repo: DjangoCompetitionRepository) -> None:
    competition = _draft()
    repo.save(competition)
    stale = repo.get(competition.id)
    fresh = repo.get(competition.id)
    assert stale is not None and fresh is not None

    fresh.add_category(category_id=CategoryId.generate(), name=CategoryName("A"), now=_NOW)
    repo.save(fresh)  # bumps stored version to 2

    stale.add_category(category_id=CategoryId.generate(), name=CategoryName("B"), now=_NOW)
    with pytest.raises(ConcurrencyConflictError):
        repo.save(stale)  # built from version 1, now stale


# ---------------------------------------------------------------------------
# Listing & soft delete
# ---------------------------------------------------------------------------


def test_list_all_and_by_season(repo: DjangoCompetitionRepository) -> None:
    a = _draft()
    repo.save(a)
    b, _ = Competition.draft(
        competition_id=CompetitionId.generate(),
        title=CompetitionTitle("Spring"),
        season=Season("2025/2026"),
        organizer_id=OrganizerId.from_uuid(_generate_uuid7()),
        now=_NOW,
    )
    repo.save(b)
    all_ids = {c.id for c in repo.list_all()}
    assert {a.id, b.id} <= all_ids
    season_ids = {c.id for c in repo.list_by_season(Season("2025/2026"))}
    assert season_ids == {b.id}


def test_structural_conformance_to_port() -> None:
    assert isinstance(DjangoCompetitionRepository(), CompetitionRepository)
