"""Unit tests for the Participants command & query handlers (use cases).

Framework-free, database-free, clock-free (ARCH-001 §28.2): every dependency is an
in-memory fake (:mod:`tests.application.participants.fakes`), time is a frozen
:class:`FakeClock`, and domain policies are used for real. Each handler is tested
for its happy path, the events it collects, persistence, and its error branches
(uniqueness, not-found, invalid input, state conflict, activation gate).
"""

from __future__ import annotations

from datetime import date

import pytest

from apps.participants.application.commands import (
    ActivateParticipantCommand,
    ArchiveParticipantCommand,
    AuthorizeInstitutionCommand,
    CreateParticipantCommand,
    ProposeGuardianLinkCommand,
    ReactivateParticipantCommand,
    ReassignDisplayAliasCommand,
    RecordConsentCommand,
    RenameParticipantCommand,
    RequestParticipantErasureCommand,
    RevokeGuardianLinkCommand,
    VerifyGuardianLinkCommand,
    VerifyParticipantCommand,
    WithdrawConsentCommand,
)
from apps.participants.application.exceptions import (
    ActivationBlockedError,
    DisplayAliasAlreadyInUseError,
    InvalidInputError,
    ParticipantNotFoundError,
    ParticipantStateConflictError,
    PolicyViolationError,
)
from apps.participants.application.handlers import (
    ActivateParticipantHandler,
    ArchiveParticipantHandler,
    AuthorizeInstitutionHandler,
    CreateParticipantHandler,
    GetParticipantHandler,
    ProposeGuardianLinkHandler,
    ReactivateParticipantHandler,
    ReassignDisplayAliasHandler,
    RecordConsentHandler,
    RenameParticipantHandler,
    RequestParticipantErasureHandler,
    RevokeGuardianLinkHandler,
    VerifyGuardianLinkHandler,
    VerifyParticipantHandler,
    WithdrawConsentHandler,
)
from apps.participants.application.queries import GetParticipantQuery
from apps.participants.domain.entities import Participant
from apps.participants.domain.events import (
    GuardianLinked,
    ParticipantActivated,
    ParticipantArchived,
    ParticipantCreated,
    ParticipantErasureRequested,
    ParticipantVerified,
)
from apps.participants.domain.policies import (
    ActivationBlockReason,
    GuardianshipPolicy,
    PseudonymizationPolicy,
)
from apps.participants.domain.value_objects import (
    ActorReference,
    ActorType,
    ConsentReference,
    DateOfBirth,
    DisplayAlias,
    GuardianId,
    GuardianRelationshipType,
    ParticipantId,
    PersonName,
    _generate_uuid7,
)
from tests.application.participants.fakes import (
    NOW,
    FakeClock,
    FakeParticipantRepository,
    FakeUuidGenerator,
)

_PSEUDONYM = PseudonymizationPolicy()
_GUARDIANSHIP = GuardianshipPolicy()


@pytest.fixture
def repo() -> FakeParticipantRepository:
    return FakeParticipantRepository()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def uuids() -> FakeUuidGenerator:
    return FakeUuidGenerator()


def _seed(
    repo: FakeParticipantRepository,
    *,
    verified: bool = False,
    with_guardian: bool = False,
    with_consent: bool = False,
    active: bool = False,
    alias: str = "Falcon-99",
) -> Participant:
    """Seed a participant driven to the requested lifecycle stage."""
    participant, _ = Participant.create(
        participant_id=ParticipantId.generate(),
        name=PersonName("Ivan", "Petrov"),
        date_of_birth=DateOfBirth(date(2015, 3, 4)),
        display_alias=DisplayAlias(alias),
        created_by=ActorReference.of(_generate_uuid7(), ActorType.GUARDIAN),
        now=NOW,
        pseudonymization_policy=_PSEUDONYM,
    )
    if verified or active:
        participant.verify(now=NOW)
    if with_guardian or active:
        guardian = GuardianId.generate()
        participant.propose_guardian_link(
            guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
        )
        participant.verify_guardian_link(guardian_id=guardian, now=NOW)
    if with_consent or active:
        participant.record_consent(
            consent=ConsentReference.of(_generate_uuid7(), "2026-01"), now=NOW
        )
    if active:
        participant.activate(policy=_GUARDIANSHIP, now=NOW)
    return repo.seed(participant)


def _create_command(**overrides: str | None) -> CreateParticipantCommand:
    fields: dict[str, str | None] = {
        "first_name": "Ivan",
        "last_name": "Petrov",
        "date_of_birth": "2015-03-04",
        "display_alias": "Falcon-99",
        "created_by_id": str(_generate_uuid7()),
        "created_by_type": "guardian",
        "middle_name": None,
    }
    fields.update(overrides)
    return CreateParticipantCommand(**fields)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CreateParticipantHandler
# ---------------------------------------------------------------------------


def test_create_happy_path(
    repo: FakeParticipantRepository, clock: FakeClock, uuids: FakeUuidGenerator
) -> None:
    handler = CreateParticipantHandler(
        participants=repo, clock=clock, uuids=uuids, pseudonymization_policy=_PSEUDONYM
    )
    result = handler.handle(_create_command())
    assert result.participant.status == "created"
    assert result.participant.display_alias == "Falcon-99"
    assert isinstance(result.events[0], ParticipantCreated)
    assert len(repo.saved) == 1


def test_create_rejects_duplicate_alias(
    repo: FakeParticipantRepository, clock: FakeClock, uuids: FakeUuidGenerator
) -> None:
    _seed(repo, alias="Falcon-99")
    handler = CreateParticipantHandler(
        participants=repo, clock=clock, uuids=uuids, pseudonymization_policy=_PSEUDONYM
    )
    with pytest.raises(DisplayAliasAlreadyInUseError):
        handler.handle(_create_command())


def test_create_rejects_unknown_actor_type(
    repo: FakeParticipantRepository, clock: FakeClock, uuids: FakeUuidGenerator
) -> None:
    handler = CreateParticipantHandler(
        participants=repo, clock=clock, uuids=uuids, pseudonymization_policy=_PSEUDONYM
    )
    with pytest.raises(InvalidInputError):
        handler.handle(_create_command(created_by_type="wizard"))


def test_create_rejects_invalid_date(
    repo: FakeParticipantRepository, clock: FakeClock, uuids: FakeUuidGenerator
) -> None:
    handler = CreateParticipantHandler(
        participants=repo, clock=clock, uuids=uuids, pseudonymization_policy=_PSEUDONYM
    )
    with pytest.raises(InvalidInputError):
        handler.handle(_create_command(date_of_birth="not-a-date"))


def test_create_rejects_identity_leaking_alias(
    repo: FakeParticipantRepository, clock: FakeClock, uuids: FakeUuidGenerator
) -> None:
    handler = CreateParticipantHandler(
        participants=repo, clock=clock, uuids=uuids, pseudonymization_policy=_PSEUDONYM
    )
    with pytest.raises(PolicyViolationError):
        handler.handle(_create_command(display_alias="Petrov art"))


# ---------------------------------------------------------------------------
# Guardian link handlers
# ---------------------------------------------------------------------------


def test_propose_guardian_link(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo)
    handler = ProposeGuardianLinkHandler(participants=repo, clock=clock)
    result = handler.handle(
        ProposeGuardianLinkCommand(
            participant_id=participant.id.json(),
            guardian_id=str(_generate_uuid7()),
            relationship_type="father",
        )
    )
    assert len(result.participant.guardian_links) == 1
    assert result.participant.guardian_links[0].status == "proposed"


def test_propose_guardian_link_bad_participant_id(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    handler = ProposeGuardianLinkHandler(participants=repo, clock=clock)
    with pytest.raises(InvalidInputError):
        handler.handle(
            ProposeGuardianLinkCommand(
                participant_id="not-a-uuid",
                guardian_id=str(_generate_uuid7()),
                relationship_type="father",
            )
        )


def test_propose_guardian_link_not_found(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    handler = ProposeGuardianLinkHandler(participants=repo, clock=clock)
    with pytest.raises(ParticipantNotFoundError):
        handler.handle(
            ProposeGuardianLinkCommand(
                participant_id=ParticipantId.generate().json(),
                guardian_id=str(_generate_uuid7()),
                relationship_type="father",
            )
        )


def test_propose_guardian_link_unknown_relationship(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    handler = ProposeGuardianLinkHandler(participants=repo, clock=clock)
    with pytest.raises(InvalidInputError):
        handler.handle(
            ProposeGuardianLinkCommand(
                participant_id=participant.id.json(),
                guardian_id=str(_generate_uuid7()),
                relationship_type="uncle",
            )
        )


def test_propose_guardian_link_bad_guardian_id(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    handler = ProposeGuardianLinkHandler(participants=repo, clock=clock)
    with pytest.raises(InvalidInputError):
        handler.handle(
            ProposeGuardianLinkCommand(
                participant_id=participant.id.json(),
                guardian_id="nope",
                relationship_type="father",
            )
        )


def test_verify_guardian_link_emits_event(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    guardian = GuardianId.generate()
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
    )
    handler = VerifyGuardianLinkHandler(participants=repo, clock=clock)
    result = handler.handle(
        VerifyGuardianLinkCommand(
            participant_id=participant.id.json(), guardian_id=guardian.json()
        )
    )
    assert isinstance(result.events[0], GuardianLinked)


def test_verify_missing_guardian_link_is_state_conflict(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    handler = VerifyGuardianLinkHandler(participants=repo, clock=clock)
    with pytest.raises(ParticipantStateConflictError) as exc:
        handler.handle(
            VerifyGuardianLinkCommand(
                participant_id=participant.id.json(), guardian_id=str(_generate_uuid7())
            )
        )
    assert exc.value.domain_code == "GuardianLinkNotFoundError"


def test_revoke_guardian_link(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo)
    guardian = GuardianId.generate()
    participant.propose_guardian_link(
        guardian_id=guardian, relationship_type=GuardianRelationshipType.MOTHER, now=NOW
    )
    handler = RevokeGuardianLinkHandler(participants=repo, clock=clock)
    result = handler.handle(
        RevokeGuardianLinkCommand(
            participant_id=participant.id.json(), guardian_id=guardian.json()
        )
    )
    assert result.participant.guardian_links[0].status == "revoked"


# ---------------------------------------------------------------------------
# Institution authority & consent handlers
# ---------------------------------------------------------------------------


def test_authorize_institution_with_teacher(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    handler = AuthorizeInstitutionHandler(participants=repo, clock=clock)
    result = handler.handle(
        AuthorizeInstitutionCommand(
            participant_id=participant.id.json(),
            institution_id=str(_generate_uuid7()),
            teacher_id=str(_generate_uuid7()),
        )
    )
    assert result.participant.institution_id is not None
    assert result.participant.teacher_id is not None


def test_authorize_institution_without_teacher(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    handler = AuthorizeInstitutionHandler(participants=repo, clock=clock)
    result = handler.handle(
        AuthorizeInstitutionCommand(
            participant_id=participant.id.json(),
            institution_id=str(_generate_uuid7()),
            teacher_id=None,
        )
    )
    assert result.participant.teacher_id is None


def test_authorize_institution_bad_id(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    handler = AuthorizeInstitutionHandler(participants=repo, clock=clock)
    with pytest.raises(InvalidInputError):
        handler.handle(
            AuthorizeInstitutionCommand(
                participant_id=participant.id.json(), institution_id="nope", teacher_id=None
            )
        )


def test_record_consent(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo)
    handler = RecordConsentHandler(participants=repo, clock=clock)
    result = handler.handle(
        RecordConsentCommand(
            participant_id=participant.id.json(),
            consent_id=str(_generate_uuid7()),
            consent_version="2026-01",
        )
    )
    assert result.participant.consent_version == "2026-01"


def test_record_consent_bad_id(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo)
    handler = RecordConsentHandler(participants=repo, clock=clock)
    with pytest.raises(InvalidInputError):
        handler.handle(
            RecordConsentCommand(
                participant_id=participant.id.json(), consent_id="nope", consent_version="1"
            )
        )


def test_withdraw_consent(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo, with_consent=True)
    handler = WithdrawConsentHandler(participants=repo, clock=clock)
    result = handler.handle(WithdrawConsentCommand(participant_id=participant.id.json()))
    assert result.participant.consent_version is None


def test_withdraw_without_consent_is_state_conflict(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    handler = WithdrawConsentHandler(participants=repo, clock=clock)
    with pytest.raises(ParticipantStateConflictError):
        handler.handle(WithdrawConsentCommand(participant_id=participant.id.json()))


# ---------------------------------------------------------------------------
# Profile handlers
# ---------------------------------------------------------------------------


def test_rename(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo)
    handler = RenameParticipantHandler(participants=repo, clock=clock)
    result = handler.handle(
        RenameParticipantCommand(
            participant_id=participant.id.json(), first_name="Ivan", last_name="Sidorov"
        )
    )
    assert result.participant.last_name == "Sidorov"


def test_reassign_display_alias(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo)
    handler = ReassignDisplayAliasHandler(
        participants=repo, clock=clock, pseudonymization_policy=_PSEUDONYM
    )
    result = handler.handle(
        ReassignDisplayAliasCommand(participant_id=participant.id.json(), display_alias="Eagle-7")
    )
    assert result.participant.display_alias == "Eagle-7"


def test_reassign_display_alias_conflict(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    _seed(repo, alias="Eagle-7")
    participant = _seed(repo, alias="Falcon-99")
    handler = ReassignDisplayAliasHandler(
        participants=repo, clock=clock, pseudonymization_policy=_PSEUDONYM
    )
    with pytest.raises(DisplayAliasAlreadyInUseError):
        handler.handle(
            ReassignDisplayAliasCommand(
                participant_id=participant.id.json(), display_alias="Eagle-7"
            )
        )


def test_reassign_display_alias_reveals_identity(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo)
    handler = ReassignDisplayAliasHandler(
        participants=repo, clock=clock, pseudonymization_policy=_PSEUDONYM
    )
    with pytest.raises(PolicyViolationError):
        handler.handle(
            ReassignDisplayAliasCommand(
                participant_id=participant.id.json(), display_alias="Petrov again"
            )
        )


# ---------------------------------------------------------------------------
# Lifecycle handlers
# ---------------------------------------------------------------------------


def test_verify_participant(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo)
    handler = VerifyParticipantHandler(participants=repo, clock=clock)
    result = handler.handle(VerifyParticipantCommand(participant_id=participant.id.json()))
    assert result.participant.status == "verified"
    assert isinstance(result.events[0], ParticipantVerified)


def test_verify_participant_wrong_state(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo, verified=True)
    handler = VerifyParticipantHandler(participants=repo, clock=clock)
    with pytest.raises(ParticipantStateConflictError):
        handler.handle(VerifyParticipantCommand(participant_id=participant.id.json()))


def test_activate_happy_path(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo, verified=True, with_guardian=True, with_consent=True)
    handler = ActivateParticipantHandler(
        participants=repo, clock=clock, guardianship_policy=_GUARDIANSHIP
    )
    result = handler.handle(ActivateParticipantCommand(participant_id=participant.id.json()))
    assert result.participant.status == "active"
    assert isinstance(result.events[0], ParticipantActivated)


def test_activate_blocked_without_consent(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo, verified=True, with_guardian=True)
    handler = ActivateParticipantHandler(
        participants=repo, clock=clock, guardianship_policy=_GUARDIANSHIP
    )
    with pytest.raises(ActivationBlockedError) as exc:
        handler.handle(ActivateParticipantCommand(participant_id=participant.id.json()))
    assert exc.value.reason == ActivationBlockReason.CONSENT_MISSING.value


def test_activate_blocked_without_adult(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo, verified=True, with_consent=True)
    handler = ActivateParticipantHandler(
        participants=repo, clock=clock, guardianship_policy=_GUARDIANSHIP
    )
    with pytest.raises(ActivationBlockedError) as exc:
        handler.handle(ActivateParticipantCommand(participant_id=participant.id.json()))
    assert exc.value.reason == ActivationBlockReason.NO_RESPONSIBLE_ADULT.value


def test_archive_and_reactivate(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo, active=True)
    archive = ArchiveParticipantHandler(participants=repo, clock=clock)
    archived = archive.handle(ArchiveParticipantCommand(participant_id=participant.id.json()))
    assert archived.participant.status == "archived"
    assert isinstance(archived.events[0], ParticipantArchived)

    reactivate = ReactivateParticipantHandler(
        participants=repo, clock=clock, guardianship_policy=_GUARDIANSHIP
    )
    reactivated = reactivate.handle(
        ReactivateParticipantCommand(participant_id=participant.id.json())
    )
    assert reactivated.participant.status == "active"


def test_request_erasure(repo: FakeParticipantRepository, clock: FakeClock) -> None:
    participant = _seed(repo, active=True)
    handler = RequestParticipantErasureHandler(participants=repo, clock=clock)
    result = handler.handle(
        RequestParticipantErasureCommand(
            participant_id=participant.id.json(), request_reference=str(_generate_uuid7())
        )
    )
    assert result.participant.status == "erased"
    assert isinstance(result.events[0], ParticipantErasureRequested)


def test_request_erasure_bad_reference(
    repo: FakeParticipantRepository, clock: FakeClock
) -> None:
    participant = _seed(repo, active=True)
    handler = RequestParticipantErasureHandler(participants=repo, clock=clock)
    with pytest.raises(InvalidInputError):
        handler.handle(
            RequestParticipantErasureCommand(
                participant_id=participant.id.json(), request_reference="nope"
            )
        )


# ---------------------------------------------------------------------------
# GetParticipantHandler (read)
# ---------------------------------------------------------------------------


def test_get_participant(repo: FakeParticipantRepository) -> None:
    participant = _seed(repo, active=True)
    handler = GetParticipantHandler(participants=repo)
    dto = handler.handle(GetParticipantQuery(participant_id=participant.id.json()))
    assert dto.id == participant.id.json()
    assert dto.status == "active"


def test_get_participant_not_found(repo: FakeParticipantRepository) -> None:
    handler = GetParticipantHandler(participants=repo)
    with pytest.raises(ParticipantNotFoundError):
        handler.handle(GetParticipantQuery(participant_id=ParticipantId.generate().json()))
