"""Integration tests for :class:`DjangoParticipantRepository`.

These exercise the repository as the real persistence adapter it is: **real Django
ORM against real PostgreSQL, no mocks** (ARCH-001 §28.2). The database is repointed
at PostgreSQL by ``tests/infrastructure/conftest.py``; every test is marked
``django_db``.

Coverage: every port method; the domain⇄persistence round trip (parent + guardian
links); insert-vs-update dispatch; optimistic locking; guardian-link
synchronization; active/non-erased alias semantics; soft delete; exception
translation; and structural conformance to the ``ParticipantRepository`` port.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from apps.participants.application.interfaces import ParticipantRepository
from apps.participants.domain.entities import Participant
from apps.participants.domain.policies import GuardianshipPolicy, PseudonymizationPolicy
from apps.participants.domain.value_objects import (
    ActorReference,
    ActorType,
    ConsentReference,
    DateOfBirth,
    DisplayAlias,
    GuardianId,
    GuardianRelationshipType,
    InstitutionId,
    ParticipantId,
    PersonName,
    TeacherId,
    _generate_uuid7,
)
from apps.participants.infrastructure.repositories import (
    ConcurrencyConflictError,
    DjangoParticipantRepository,
    IntegrityViolationError,
)

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
_PSEUDONYM = PseudonymizationPolicy()
_GUARDIANSHIP = GuardianshipPolicy()


def make_participant(*, alias: str = "Falcon-99") -> Participant:
    """A freshly-created aggregate (version 1, Created)."""
    participant, _ = Participant.create(
        participant_id=ParticipantId.generate(),
        name=PersonName("Ivan", "Petrov", "Sergeevich"),
        date_of_birth=DateOfBirth(date(2015, 3, 4)),
        display_alias=DisplayAlias(alias),
        created_by=ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
        now=_NOW,
        pseudonymization_policy=_PSEUDONYM,
    )
    return participant


@pytest.fixture
def repo() -> DjangoParticipantRepository:
    return DjangoParticipantRepository()


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_save_then_get_minimal(repo: DjangoParticipantRepository) -> None:
    participant = make_participant()
    repo.save(participant)
    loaded = repo.get(participant.id)
    assert loaded is not None
    assert loaded.id == participant.id
    assert loaded.display_alias == participant.display_alias
    assert loaded.status is participant.status
    assert loaded.guardian_links == ()
    assert loaded.version == 1


def test_save_then_get_full(repo: DjangoParticipantRepository) -> None:
    participant = make_participant()
    participant.verify(now=_NOW)
    guardian = GuardianId.generate()
    participant.propose_guardian_link(guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=_NOW)
    participant.verify_guardian_link(guardian_id=guardian, now=_NOW)
    participant.authorize_institution(institution_id=InstitutionId.generate(), teacher_id=TeacherId.generate(), now=_NOW)
    participant.record_consent(consent=ConsentReference.of(_generate_uuid7(), "2026-01"), now=_NOW)
    participant.activate(policy=_GUARDIANSHIP, now=_NOW)
    repo.save(participant)

    loaded = repo.get(participant.id)
    assert loaded is not None
    assert loaded.status.value == "active"
    assert loaded.active_guardian_count() == 1
    assert loaded.has_institutional_authority()
    assert loaded.has_active_consent()
    assert loaded.guardian_links[0].guardian_id == guardian


def test_get_missing_returns_none(repo: DjangoParticipantRepository) -> None:
    assert repo.get(ParticipantId.generate()) is None


# ---------------------------------------------------------------------------
# Insert vs update, optimistic concurrency
# ---------------------------------------------------------------------------


def test_update_dispatch_persists_changes(repo: DjangoParticipantRepository) -> None:
    participant = make_participant()
    repo.save(participant)  # insert
    participant.verify(now=_NOW)
    repo.save(participant)  # update
    loaded = repo.get(participant.id)
    assert loaded is not None
    assert loaded.status.value == "verified"
    assert loaded.version == 2


def test_stale_write_raises_concurrency_conflict(repo: DjangoParticipantRepository) -> None:
    participant = make_participant()
    repo.save(participant)
    first = repo.get(participant.id)
    second = repo.get(participant.id)
    assert first is not None and second is not None
    first.verify(now=_NOW)
    repo.save(first)  # advances stored version to 2
    second.verify(now=_NOW)  # still built from version 1
    with pytest.raises(ConcurrencyConflictError):
        repo.save(second)


def test_duplicate_active_alias_raises_integrity(repo: DjangoParticipantRepository) -> None:
    repo.save(make_participant(alias="Falcon-99"))
    with pytest.raises(IntegrityViolationError):
        repo.save(make_participant(alias="Falcon-99"))


# ---------------------------------------------------------------------------
# Guardian-link synchronization
# ---------------------------------------------------------------------------


def test_guardian_links_are_synchronized(repo: DjangoParticipantRepository) -> None:
    # One save per business operation, mirroring the handler unit-of-work: each
    # domain method bumps the version once and the save is conditional on the
    # previous version (optimistic concurrency).
    participant = make_participant()
    repo.save(participant)
    guardian_a = GuardianId.generate()
    participant.propose_guardian_link(guardian_id=guardian_a, relationship_type=GuardianRelationshipType.MOTHER, now=_NOW)
    repo.save(participant)
    participant.verify_guardian_link(guardian_id=guardian_a, now=_NOW)
    repo.save(participant)

    # Revoke A and add B across separate saves; the child rows must reflect the set.
    participant.revoke_guardian_link(guardian_id=guardian_a, now=_NOW)
    repo.save(participant)
    guardian_b = GuardianId.generate()
    participant.propose_guardian_link(guardian_id=guardian_b, relationship_type=GuardianRelationshipType.FATHER, now=_NOW)
    repo.save(participant)

    loaded = repo.get(participant.id)
    assert loaded is not None
    statuses = {link.guardian_id: link.status.value for link in loaded.guardian_links}
    assert statuses[guardian_a] == "revoked"
    assert statuses[guardian_b] == "proposed"


# ---------------------------------------------------------------------------
# Alias lookups & existence
# ---------------------------------------------------------------------------


def test_alias_lookups_and_existence(repo: DjangoParticipantRepository) -> None:
    participant = make_participant(alias="Falcon-99")
    repo.save(participant)
    alias = DisplayAlias("Falcon-99")
    assert repo.exists(participant.id) is True
    assert repo.exists(ParticipantId.generate()) is False
    assert repo.exists_by_display_alias(alias) is True
    found = repo.get_by_display_alias(alias)
    assert found is not None and found.id == participant.id
    assert repo.get_by_display_alias(DisplayAlias("Nobody")) is None


def test_erased_participant_frees_alias(repo: DjangoParticipantRepository) -> None:
    participant = make_participant(alias="Falcon-99")
    participant.verify(now=_NOW)
    guardian = GuardianId.generate()
    participant.propose_guardian_link(guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=_NOW)
    participant.verify_guardian_link(guardian_id=guardian, now=_NOW)
    participant.record_consent(consent=ConsentReference.of(_generate_uuid7(), "1"), now=_NOW)
    participant.activate(policy=_GUARDIANSHIP, now=_NOW)
    participant.request_erasure(request_reference=_generate_uuid7(), now=_NOW)
    repo.save(participant)

    alias = DisplayAlias("Falcon-99")
    assert repo.exists_by_display_alias(alias) is False
    assert repo.get_by_display_alias(alias) is None
    # The row is retained and still fetchable by id.
    loaded = repo.get(participant.id)
    assert loaded is not None and loaded.status.value == "erased"


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


def test_delete_soft_deletes_and_is_idempotent(repo: DjangoParticipantRepository) -> None:
    participant = make_participant(alias="Falcon-99")
    repo.save(participant)
    repo.delete(participant)
    alias = DisplayAlias("Falcon-99")
    assert repo.exists_by_display_alias(alias) is False
    assert repo.get(participant.id) is not None  # retained for audit
    # Idempotent: deleting again and deleting a never-saved participant are no-ops.
    repo.delete(participant)
    repo.delete(make_participant(alias="Ghost-1"))


# ---------------------------------------------------------------------------
# Structural conformance
# ---------------------------------------------------------------------------


def test_repository_conforms_to_port() -> None:
    assert isinstance(DjangoParticipantRepository(), ParticipantRepository)
