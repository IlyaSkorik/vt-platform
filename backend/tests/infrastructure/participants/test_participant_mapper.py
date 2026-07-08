"""Unit tests for :class:`ParticipantMapper`.

Pure, database-free translation tests (ARCH-001 §28.2): they build **unsaved** ORM
instances and domain aggregates in memory and assert the mapper round-trips them
field-for-field, covering the optional institution/teacher/consent branches and the
guardian-link child rows. Persistence of these rows is the repository's concern and
is exercised separately against real PostgreSQL.
"""

from __future__ import annotations

from datetime import date

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
from apps.participants.infrastructure.mappers import ParticipantMapper
from tests.application.participants.fakes import NOW

_PSEUDONYM = PseudonymizationPolicy()
_GUARDIANSHIP = GuardianshipPolicy()


def _new(*, alias: str = "Falcon-99") -> Participant:
    participant, _ = Participant.create(
        participant_id=ParticipantId.generate(),
        name=PersonName("Ivan", "Petrov", "Sergeevich"),
        date_of_birth=DateOfBirth(date(2015, 3, 4)),
        display_alias=DisplayAlias(alias),
        created_by=ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
        now=NOW,
        pseudonymization_policy=_PSEUDONYM,
    )
    return participant


def _active(participant: Participant) -> Participant:
    participant.verify(now=NOW)
    guardian = GuardianId.generate()
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
    )
    participant.verify_guardian_link(guardian_id=guardian, now=NOW)
    participant.authorize_institution(
        institution_id=InstitutionId.generate(), teacher_id=TeacherId.generate(), now=NOW
    )
    participant.record_consent(consent=ConsentReference.of(_generate_uuid7(), "2026-01"), now=NOW)
    participant.activate(policy=_GUARDIANSHIP, now=NOW)
    return participant


def test_round_trip_minimal() -> None:
    entity = _new()
    model = ParticipantMapper.to_model(entity)
    links = ParticipantMapper.to_guardian_link_models(entity)
    restored = ParticipantMapper.to_domain(model, links)
    assert restored.id == entity.id
    assert restored.status is entity.status
    assert restored.name.full == entity.name.full
    assert restored.display_alias == entity.display_alias
    assert restored.date_of_birth == entity.date_of_birth
    assert restored.institution_authority is None
    assert restored.consent is None
    assert restored.guardian_links == ()
    assert restored.version == entity.version


def test_round_trip_full() -> None:
    entity = _active(_new())
    model = ParticipantMapper.to_model(entity)
    links = ParticipantMapper.to_guardian_link_models(entity)
    restored = ParticipantMapper.to_domain(model, links)
    assert restored.status.value == "active"
    restored_authority = restored.institution_authority
    original_authority = entity.institution_authority
    assert restored_authority is not None
    assert original_authority is not None
    assert restored_authority.institution_id == original_authority.institution_id
    assert restored_authority.teacher_id == original_authority.teacher_id
    assert restored.consent == entity.consent
    assert restored.active_guardian_count() == 1
    restored_link = restored.guardian_links[0]
    original_link = entity.guardian_links[0]
    assert restored_link.guardian_id == original_link.guardian_id
    assert restored_link.status is original_link.status
    assert restored_link.relationship_type is original_link.relationship_type
    assert restored_link.established_at == original_link.established_at


def test_institution_without_teacher_round_trips() -> None:
    entity = _new()
    entity.authorize_institution(institution_id=InstitutionId.generate(), now=NOW)
    model = ParticipantMapper.to_model(entity)
    restored = ParticipantMapper.to_domain(model, [])
    assert restored.institution_authority is not None
    assert restored.institution_authority.teacher_id is None


def test_to_guardian_link_models_projects_rows() -> None:
    entity = _active(_new())
    rows = ParticipantMapper.to_guardian_link_models(entity)
    assert len(rows) == 1
    row = rows[0]
    assert row.participant_id == entity.id.value
    assert row.guardian_id == entity.guardian_links[0].guardian_id.value
    assert row.status == "active"
    assert row.relationship_type == "mother"
    assert str(row)  # __str__ smoke


def test_update_model_reprojects_columns() -> None:
    entity = _new()
    model = ParticipantMapper.to_model(entity)
    assert str(model)  # __str__ smoke
    entity.verify(now=NOW)
    updated = ParticipantMapper.update_model(model, entity)
    assert updated.status == "verified"
    assert updated.version == entity.version
    assert updated.verified_at == NOW
