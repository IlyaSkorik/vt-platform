"""Attachment use cases: attach a file, remove an attachment."""

from __future__ import annotations

from pathlib import PurePosixPath

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    AttachFileCommand,
    RemoveAttachmentCommand,
    UploadAttachmentCommand,
)
from apps.applications.application.exceptions import (
    DeadlinePassedError,
    FileTooLargeError,
    InvalidInputError,
    UnsupportedFileTypeError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    Clock,
    CompetitionCatalog,
    CompetitionUploadPolicy,
    EventPublisher,
    FileStorage,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.value_objects import AttachmentId, AttachmentType, FileReference

from ._support import ensure_owner, load_submission, parse_submission_id, parse_user_id

__all__ = ["AttachFileHandler", "RemoveAttachmentHandler", "UploadAttachmentHandler"]


def _parse_attachment_type(raw: str) -> AttachmentType:
    try:
        return AttachmentType(raw)
    except ValueError as exc:
        raise InvalidInputError(f"{raw!r} is not a valid attachment type.") from exc


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


class UploadAttachmentHandler:
    """Use case: validate, store and attach an uploaded file to the submission.

    Validation reuses the competition's upload constraints (size + allowed
    extensions) for the file's kind; only then are the bytes stored and the
    resulting reference attached to the submission. The domain enforces that
    attachments may only be added while the submission is editable.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        storage: FileStorage,
        upload_policy: CompetitionUploadPolicy,
        catalog: CompetitionCatalog,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._storage = storage
        self._upload_policy = upload_policy
        self._catalog = catalog
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: UploadAttachmentCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        attachment_type = _parse_attachment_type(command.attachment_type)

        if not self._catalog.accepts_upload(competition_id=submission.competition_id, attachment_kind=attachment_type.value, now=now):
            raise DeadlinePassedError(f"The upload deadline for {attachment_type.value} in this competition has passed.")

        performance = submission.performance
        participation_format_id = performance.participation_format_id.json() if performance is not None else None
        constraints = self._upload_policy.limits_for(
            competition_id=submission.competition_id,
            attachment_kind=attachment_type.value,
            participation_format_id=participation_format_id,
        )
        if len(command.content) > constraints.max_bytes:
            raise FileTooLargeError(
                f"The file is {len(command.content)} bytes; the maximum for {attachment_type.value} is {constraints.max_bytes} bytes."
            )
        extension = PurePosixPath(command.filename).suffix.lstrip(".").lower()
        if not constraints.allows_extension(extension):
            raise UnsupportedFileTypeError(f"Files of type {extension or '(none)'!r} are not allowed for {attachment_type.value}.")

        reference = self._storage.save(content=command.content, filename=command.filename, content_type=command.content_type)
        attachment_id = AttachmentId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            file_reference = FileReference(reference)
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
