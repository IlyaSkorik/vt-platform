"""Command & query handlers (use cases) for the Participants bounded context.

One handler per command (plus a read handler for retrieval). A handler is a thin
**orchestrator**: it holds no business rules of its own (those live in the domain)
and no persistence details (those live in infrastructure). It depends only on
application **ports** (:mod:`apps.participants.application.interfaces`) and injected
domain **policies**, and follows one shape:

    1. resolve the current instant from the :class:`Clock`;
    2. load the aggregate (or, for creation, mint identity + create);
    3. build validated value objects from the command's raw fields;
    4. execute the aggregate's behaviour, **receiving** the domain events;
    5. persist the aggregate through the :class:`ParticipantRepository`;
    6. return an :class:`OperationResultDto` carrying the new state **and** the
       collected events.

**Events are collected, never published.** A handler returns the events the domain
produced; a future Unit of Work will commit the aggregate and forward them to the
outbox / event dispatcher (ARCH-001 §4.8).

**Errors are translated, never swallowed.** Domain-touching steps run inside
:func:`~apps.participants.application.exceptions.translate_domain_errors`, which
re-raises domain errors as application errors (preserving the cause). Cross-
aggregate uniqueness and "not found" are application concerns raised directly here.

This module imports nothing from infrastructure, presentation, or Django.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

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
from apps.participants.application.dto import OperationResultDto, ParticipantDto
from apps.participants.application.exceptions import (
    DisplayAliasAlreadyInUseError,
    InvalidInputError,
    ParticipantNotFoundError,
    translate_domain_errors,
)
from apps.participants.application.interfaces import Clock, ParticipantRepository, UuidGenerator
from apps.participants.application.queries import GetParticipantQuery
from apps.participants.domain.entities import Participant
from apps.participants.domain.events import DomainEvent
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
)

__all__ = [
    "ActivateParticipantHandler",
    "ArchiveParticipantHandler",
    "AuthorizeInstitutionHandler",
    "CreateParticipantHandler",
    "GetParticipantHandler",
    "ProposeGuardianLinkHandler",
    "ReactivateParticipantHandler",
    "ReassignDisplayAliasHandler",
    "RecordConsentHandler",
    "RenameParticipantHandler",
    "RequestParticipantErasureHandler",
    "RevokeGuardianLinkHandler",
    "VerifyGuardianLinkHandler",
    "VerifyParticipantHandler",
    "WithdrawConsentHandler",
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load_participant(participants: ParticipantRepository, raw_id: str) -> Participant:
    """Resolve ``raw_id`` and load the aggregate, or raise application errors.

    A malformed id becomes :class:`InvalidInputError`; a well-formed id with no
    stored participant becomes :class:`ParticipantNotFoundError`.
    """
    with translate_domain_errors():
        participant_id = ParticipantId.from_string(raw_id)
    participant = participants.get(participant_id)
    if participant is None:
        raise ParticipantNotFoundError(f"No participant found with id {raw_id!r}.")
    return participant


def _parse_actor_type(raw: str) -> ActorType:
    """Map a raw actor-type string to an :class:`ActorType`."""
    try:
        return ActorType(raw)
    except ValueError as exc:
        raise InvalidInputError(f"Unknown actor type {raw!r}.") from exc


def _parse_relationship_type(raw: str) -> GuardianRelationshipType:
    """Map a raw relationship-type string to a :class:`GuardianRelationshipType`."""
    try:
        return GuardianRelationshipType(raw)
    except ValueError as exc:
        raise InvalidInputError(f"Unknown relationship type {raw!r}.") from exc


def _parse_reference(raw: str) -> uuid.UUID:
    """Parse a request/erasure reference into a :class:`uuid.UUID`."""
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError) as exc:
        raise InvalidInputError(f"{raw!r} is not a valid reference.") from exc


def _result(participant: Participant, events: Sequence[DomainEvent]) -> OperationResultDto:
    """Render the post-operation aggregate and its events into a result DTO."""
    return OperationResultDto(participant=ParticipantDto.from_participant(participant), events=tuple(events))


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class CreateParticipantHandler:
    """Use case: register a brand-new participant.

    Validates value objects, enforces display-alias uniqueness across participants,
    guards the alias against leaking the real name (JDG-006), mints a UUID v7
    identity, and creates the aggregate in ``Created``.
    """

    def __init__(
        self,
        *,
        participants: ParticipantRepository,
        clock: Clock,
        uuids: UuidGenerator,
        pseudonymization_policy: PseudonymizationPolicy,
    ) -> None:
        self._participants = participants
        self._clock = clock
        self._uuids = uuids
        self._pseudonymization_policy = pseudonymization_policy

    def handle(self, command: CreateParticipantCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        actor_type = _parse_actor_type(command.created_by_type)
        with translate_domain_errors():
            name = PersonName.of(command.first_name, command.last_name, command.middle_name)
            date_of_birth = DateOfBirth.from_iso(command.date_of_birth)
            display_alias = DisplayAlias(command.display_alias)
            created_by = ActorReference.of(command.created_by_id, actor_type)

        if self._participants.exists_by_display_alias(display_alias):
            raise DisplayAliasAlreadyInUseError(f"Display alias {display_alias.value!r} is already in use.")

        participant_id = ParticipantId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            participant, events = Participant.create(
                participant_id=participant_id,
                name=name,
                date_of_birth=date_of_birth,
                display_alias=display_alias,
                created_by=created_by,
                now=now,
                pseudonymization_policy=self._pseudonymization_policy,
            )
        self._participants.save(participant)
        return _result(participant, events)


# ---------------------------------------------------------------------------
# Guardian relationships
# ---------------------------------------------------------------------------


class ProposeGuardianLinkHandler:
    """Use case: propose a guardian relationship for a participant."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: ProposeGuardianLinkCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        relationship_type = _parse_relationship_type(command.relationship_type)
        with translate_domain_errors():
            guardian_id = GuardianId.from_string(command.guardian_id)
            events = participant.propose_guardian_link(guardian_id=guardian_id, relationship_type=relationship_type, now=now)
        self._participants.save(participant)
        return _result(participant, events)


class VerifyGuardianLinkHandler:
    """Use case: verify a proposed guardian relationship (emits GuardianLinked)."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: VerifyGuardianLinkCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            guardian_id = GuardianId.from_string(command.guardian_id)
            events = participant.verify_guardian_link(guardian_id=guardian_id, now=now)
        self._participants.save(participant)
        return _result(participant, events)


class RevokeGuardianLinkHandler:
    """Use case: revoke a guardian relationship."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: RevokeGuardianLinkCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            guardian_id = GuardianId.from_string(command.guardian_id)
            events = participant.revoke_guardian_link(guardian_id=guardian_id, now=now)
        self._participants.save(participant)
        return _result(participant, events)


# ---------------------------------------------------------------------------
# Institutional authority & consent
# ---------------------------------------------------------------------------


class AuthorizeInstitutionHandler:
    """Use case: record an authorizing institution (and optional teacher) link (PRT-001)."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: AuthorizeInstitutionCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            institution_id = InstitutionId.from_string(command.institution_id)
            teacher_id = TeacherId.from_string(command.teacher_id) if command.teacher_id is not None else None
            events = participant.authorize_institution(institution_id=institution_id, teacher_id=teacher_id, now=now)
        self._participants.save(participant)
        return _result(participant, events)


class RecordConsentHandler:
    """Use case: record that an active Identity consent authorizes this participant."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: RecordConsentCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            consent = ConsentReference.of(command.consent_id, command.consent_version)
            events = participant.record_consent(consent=consent, now=now)
        self._participants.save(participant)
        return _result(participant, events)


class WithdrawConsentHandler:
    """Use case: clear the recorded consent for a participant."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: WithdrawConsentCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            events = participant.withdraw_consent(now=now)
        self._participants.save(participant)
        return _result(participant, events)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class RenameParticipantHandler:
    """Use case: correct a participant's minimized real name."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: RenameParticipantCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            name = PersonName.of(command.first_name, command.last_name, command.middle_name)
            events = participant.rename(name, now=now)
        self._participants.save(participant)
        return _result(participant, events)


class ReassignDisplayAliasHandler:
    """Use case: change a participant's judging alias, keeping it unique and safe (JDG-006)."""

    def __init__(
        self,
        *,
        participants: ParticipantRepository,
        clock: Clock,
        pseudonymization_policy: PseudonymizationPolicy,
    ) -> None:
        self._participants = participants
        self._clock = clock
        self._pseudonymization_policy = pseudonymization_policy

    def handle(self, command: ReassignDisplayAliasCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            display_alias = DisplayAlias(command.display_alias)
        owner = self._participants.get_by_display_alias(display_alias)
        if owner is not None and owner.id != participant.id:
            raise DisplayAliasAlreadyInUseError(f"Display alias {display_alias.value!r} is already in use.")
        with translate_domain_errors():
            events = participant.reassign_display_alias(display_alias, pseudonymization_policy=self._pseudonymization_policy, now=now)
        self._participants.save(participant)
        return _result(participant, events)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class VerifyParticipantHandler:
    """Use case: verify a participant's details (``Created → Verified``)."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: VerifyParticipantCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            events = participant.verify(now=now)
        self._participants.save(participant)
        return _result(participant, events)


class ActivateParticipantHandler:
    """Use case: activate a participant (``Verified → Active``), subject to PRT-001."""

    def __init__(
        self,
        *,
        participants: ParticipantRepository,
        clock: Clock,
        guardianship_policy: GuardianshipPolicy,
    ) -> None:
        self._participants = participants
        self._clock = clock
        self._guardianship_policy = guardianship_policy

    def handle(self, command: ActivateParticipantCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            events = participant.activate(policy=self._guardianship_policy, now=now)
        self._participants.save(participant)
        return _result(participant, events)


class ArchiveParticipantHandler:
    """Use case: archive a participant (``Active → Archived``)."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: ArchiveParticipantCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            events = participant.archive(now=now)
        self._participants.save(participant)
        return _result(participant, events)


class ReactivateParticipantHandler:
    """Use case: reactivate an archived participant (``Archived → Active``)."""

    def __init__(
        self,
        *,
        participants: ParticipantRepository,
        clock: Clock,
        guardianship_policy: GuardianshipPolicy,
    ) -> None:
        self._participants = participants
        self._clock = clock
        self._guardianship_policy = guardianship_policy

    def handle(self, command: ReactivateParticipantCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        with translate_domain_errors():
            events = participant.reactivate(policy=self._guardianship_policy, now=now)
        self._participants.save(participant)
        return _result(participant, events)


class RequestParticipantErasureHandler:
    """Use case: request erasure of a participant (``{Active|Archived} → Erased``, PRT-007)."""

    def __init__(self, *, participants: ParticipantRepository, clock: Clock) -> None:
        self._participants = participants
        self._clock = clock

    def handle(self, command: RequestParticipantErasureCommand) -> OperationResultDto:
        now = self._clock.utcnow()
        participant = _load_participant(self._participants, command.participant_id)
        request_reference = _parse_reference(command.request_reference)
        with translate_domain_errors():
            events = participant.request_erasure(request_reference=request_reference, now=now)
        self._participants.save(participant)
        return _result(participant, events)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class GetParticipantHandler:
    """Read use case: retrieve a single participant projection by identifier.

    Side-effect-free: it loads the aggregate and returns its :class:`ParticipantDto`
    projection, never mutating state and emitting no events.
    """

    def __init__(self, *, participants: ParticipantRepository) -> None:
        self._participants = participants

    def handle(self, query: GetParticipantQuery) -> ParticipantDto:
        participant = _load_participant(self._participants, query.participant_id)
        return ParticipantDto.from_participant(participant)
