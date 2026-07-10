"""Attachment use cases: attach a file, remove an attachment."""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    AttachFileCommand,
    RemoveAttachmentCommand,
)
from apps.applications.application.exceptions import (
    InvalidInputError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    Clock,
    EventPublisher,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.value_objects import AttachmentId, AttachmentType, FileReference

from ._support import ensure_owner, load_submission, parse_submission_id, parse_user_id

__all__ = ["AttachFileHandler", "RemoveAttachmentHandler"]


class AttachFileHandler:
    """Use case: attach a file reference to the submission."""

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

    def handle(self, command: AttachFileCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))

        try:
            attachment_type = AttachmentType(command.attachment_type)
        except ValueError as exc:
            raise InvalidInputError(f"{command.attachment_type!r} is not a valid attachment type.") from exc
        attachment_id = AttachmentId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            file_reference = FileReference(command.file_reference)
            domain_events = submission.add_attachment(
                attachment_id=attachment_id,
                attachment_type=attachment_type,
                file=file_reference,
                now=now,
                caption=command.caption,
            )
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class RemoveAttachmentHandler:
    """Use case: remove an attachment reference from the submission."""

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

    def handle(self, command: RemoveAttachmentCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        with translate_domain_errors():
            attachment_id = AttachmentId.from_string(command.attachment_id)
            domain_events = submission.remove_attachment(attachment_id=attachment_id, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
