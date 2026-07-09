"""Unit tests for the Participants result DTOs.

Verifies the flat projection of the ``Participant`` aggregate — including the
optional institution/teacher/consent fields (present and absent) and the guardian
links — into a serialization-agnostic :class:`ParticipantDto`.
"""

from __future__ import annotations

from datetime import date

from apps.participants.application.dto import GuardianLinkDto, OperationResultDto, ParticipantDto
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
from tests.application.participants.fakes import NOW

_PSEUDONYM = PseudonymizationPolicy()
_GUARDIANSHIP = GuardianshipPolicy()


def _new() -> Participant:
    participant, _ = Participant.create(
        participant_id=ParticipantId.generate(),
        name=PersonName("Ivan", "Petrov", "Sergeevich"),
        date_of_birth=DateOfBirth(date(2015, 3, 4)),
        display_alias=DisplayAlias("Falcon-99"),
        created_by=ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
        now=NOW,
        pseudonymization_policy=_PSEUDONYM,
    )
    return participant


def test_participant_dto_minimal_projection() -> None:
    participant = _new()
    dto = ParticipantDto.from_participant(participant)
    assert dto.id == participant.id.json()
    assert dto.full_name == "Ivan Sergeevich Petrov"
    assert dto.middle_name == "Sergeevich"
    assert dto.date_of_birth == "2015-03-04"
    assert dto.created_by_type == "guardian"
    assert dto.institution_id is None
    assert dto.teacher_id is None
    assert dto.consent_id is None
    assert dto.consent_version is None
    assert dto.guardian_links == ()
    assert dto.version == 1


def test_participant_dto_full_projection() -> None:
    participant = _new()
    participant.verify(now=NOW)
    guardian = GuardianId.generate()
    participant.propose_guardian_link(guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW)
    participant.verify_guardian_link(guardian_id=guardian, now=NOW)
    participant.authorize_institution(institution_id=InstitutionId.generate(), teacher_id=TeacherId.generate(), now=NOW)
    participant.record_consent(consent=ConsentReference.of(_generate_uuid7(), "2026-01"), now=NOW)
    participant.activate(policy=_GUARDIANSHIP, now=NOW)

    dto = ParticipantDto.from_participant(participant)
    assert dto.status == "active"
    assert dto.institution_id is not None
    assert dto.teacher_id is not None
    assert dto.consent_version == "2026-01"
    assert len(dto.guardian_links) == 1
    link = dto.guardian_links[0]
    assert isinstance(link, GuardianLinkDto)
    assert link.guardian_id == guardian.json()
    assert link.status == "active"
    assert link.relationship_type == "mother"
    assert link.established_at == NOW


def test_participant_dto_institution_without_teacher() -> None:
    participant = _new()
    participant.authorize_institution(institution_id=InstitutionId.generate(), now=NOW)
    dto = ParticipantDto.from_participant(participant)
    assert dto.institution_id is not None
    assert dto.teacher_id is None


def test_operation_result_carries_participant_and_events() -> None:
    participant = _new()
    events = participant.verify(now=NOW)
    result = OperationResultDto(participant=ParticipantDto.from_participant(participant), events=tuple(events))
    assert result.participant.status == "verified"
    assert len(result.events) == 1
