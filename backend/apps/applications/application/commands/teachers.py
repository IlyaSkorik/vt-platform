"""Teacher use cases: add, update (replace), remove a teacher."""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    AddTeacherCommand,
    RemoveTeacherCommand,
    UpdateTeacherCommand,
)
from apps.applications.application.exceptions import (
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
from apps.applications.domain.value_objects import DirectoryTeacherId, PersonName, TeacherId, TeacherRole

from ._support import ensure_owner, load_submission, parse_submission_id, parse_user_id

__all__ = ["AddTeacherHandler", "RemoveTeacherHandler", "UpdateTeacherHandler"]


def _parse_person(*, first_name: str, last_name: str, middle_name: str | None) -> PersonName:
    with translate_domain_errors():
        return PersonName(first_name=first_name, last_name=last_name, middle_name=middle_name)


def _parse_directory_teacher_id(raw: str | None) -> DirectoryTeacherId | None:
    if not raw:
        return None
    with translate_domain_errors():
        return DirectoryTeacherId.from_string(raw)


class AddTeacherHandler:
    """Use case: add a teacher in a configurable role."""

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

    def handle(self, command: AddTeacherCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))

        name = _parse_person(first_name=command.first_name, last_name=command.last_name, middle_name=command.middle_name)
        directory_teacher_id = _parse_directory_teacher_id(command.directory_teacher_id)
        teacher_id = TeacherId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            role = TeacherRole(command.role)
            domain_events = submission.add_teacher(teacher_id=teacher_id, name=name, role=role, directory_teacher_id=directory_teacher_id, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class UpdateTeacherHandler:
    """Use case: replace a teacher's details.

    Like participants, the replacement is added first and the original removed
    after, so the replacement receives a fresh ``TeacherId``.
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

    def handle(self, command: UpdateTeacherCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        with translate_domain_errors():
            target_id = TeacherId.from_string(command.teacher_id)
        target = next((t for t in submission.teachers if t.id == target_id), None)
        if target is None:
            raise SubmissionChildNotFoundError(
                f"No teacher {target_id.json()} in this submission.",
                domain_code="TeacherNotFoundError",
            )

        name = _parse_person(first_name=command.first_name, last_name=command.last_name, middle_name=command.middle_name)
        new_id = TeacherId.from_uuid(self._uuids.new())
        domain_events: list[DomainEvent] = []
        with translate_domain_errors():
            role = TeacherRole(command.role)
            # Preserve the directory link across the replace so the credit still
            # points at the same reusable Teacher Directory entry.
            domain_events += submission.add_teacher(
                teacher_id=new_id, name=name, role=role, directory_teacher_id=target.directory_teacher_id, now=now
            )
            domain_events += submission.remove_teacher(teacher_id=target_id, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class RemoveTeacherHandler:
    """Use case: remove a teacher from the submission."""

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

    def handle(self, command: RemoveTeacherCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        with translate_domain_errors():
            teacher_id = TeacherId.from_string(command.teacher_id)
            domain_events = submission.remove_teacher(teacher_id=teacher_id, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
