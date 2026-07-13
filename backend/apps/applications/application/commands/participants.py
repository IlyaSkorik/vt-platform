"""Participant use cases: add, update (replace), remove a participant."""

from __future__ import annotations

from datetime import date

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    AddParticipantCommand,
    RemoveParticipantCommand,
    UpdateParticipantCommand,
)
from apps.applications.application.exceptions import (
    InvalidInputError,
    SubmissionChildNotFoundError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    Clock,
    EventPublisher,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    BirthDate,
    Gender,
    ParticipantId,
    PersonName,
    RegistryParticipantId,
)

from ._support import ensure_owner, load_submission, parse_submission_id, parse_user_id

__all__ = [
    "AddParticipantHandler",
    "RemoveParticipantHandler",
    "UpdateParticipantHandler",
]


def _parse_person(*, first_name: str, last_name: str, middle_name: str | None) -> PersonName:
    with translate_domain_errors():
        return PersonName(first_name=first_name, last_name=last_name, middle_name=middle_name)


def _parse_birth_date(raw: str) -> BirthDate:
    try:
        parsed = date.fromisoformat(raw)
    except (ValueError, TypeError) as exc:
        raise InvalidInputError(f"{raw!r} is not a valid ISO-8601 date.") from exc
    with translate_domain_errors():
        return BirthDate(parsed)


def _parse_gender(raw: str) -> Gender:
    try:
        return Gender(raw)
    except ValueError as exc:
        raise InvalidInputError(f"{raw!r} is not a valid gender.") from exc


def _parse_registry_id(raw: str) -> RegistryParticipantId:
    with translate_domain_errors():
        return RegistryParticipantId.from_string(raw)


class AddParticipantHandler:
    """Use case: add a participant to the submission."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: AddParticipantCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))

        # A solo participant supplies a structured name; a collective supplies only a
        # display name. Birth date and gender are present for a solo, absent for a
        # collective. The registry id links back to the reusable Participant Registry.
        name = (
            _parse_person(first_name=command.first_name, last_name=command.last_name, middle_name=command.middle_name)
            if command.first_name and command.last_name
            else None
        )
        birth_date = _parse_birth_date(command.birth_date) if command.birth_date else None
        gender = _parse_gender(command.gender) if command.gender else None
        registry_id = _parse_registry_id(command.registry_participant_id) if command.registry_participant_id else None
        display_name = command.display_name.strip() if command.display_name else None
        participant_id = ParticipantId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            domain_events = submission.add_participant(
                participant_id=participant_id,
                name=name,
                birth_date=birth_date,
                gender=gender,
                display_name=display_name,
                registry_participant_id=registry_id,
                member_count=command.member_count,
                now=now,
            )
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class UpdateParticipantHandler:
    """Use case: replace a participant's details.

    The domain models participants as add/remove only, so the replacement is added
    first (keeping the "at least one participant" invariant intact even when the
    edited one is the sole participant) and the original removed after. The
    replacement therefore receives a fresh ``ParticipantId``. Editing only the
    non-key fields of a participant whose (name, birth date) is unchanged is
    rejected by the domain's duplicate rule - a known limitation of the current
    frozen domain (see the layer notes).
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: UpdateParticipantCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        with translate_domain_errors():
            target_id = ParticipantId.from_string(command.participant_id)
        if not any(p.id == target_id for p in submission.participants):
            raise SubmissionChildNotFoundError(
                f"No participant {target_id.json()} in this submission.",
                domain_code="ParticipantNotFoundError",
            )

        name = _parse_person(first_name=command.first_name, last_name=command.last_name, middle_name=command.middle_name)
        birth_date = _parse_birth_date(command.birth_date)
        gender = _parse_gender(command.gender)
        new_id = ParticipantId.from_uuid(self._uuids.new())
        domain_events: list[DomainEvent] = []
        with translate_domain_errors():
            domain_events += submission.add_participant(
                participant_id=new_id,
                name=name,
                birth_date=birth_date,
                gender=gender,
                now=now,
            )
            domain_events += submission.remove_participant(participant_id=target_id, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class RemoveParticipantHandler:
    """Use case: remove a participant from the submission."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._clock = clock
        self._events = events

    def handle(self, command: RemoveParticipantCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        with translate_domain_errors():
            participant_id = ParticipantId.from_string(command.participant_id)
            domain_events = submission.remove_participant(participant_id=participant_id, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
