"""Attachment use cases: attach a file, remove an attachment.

Each one comes in two: the applicant's, which proves ownership and honours the
competition's upload deadline, and the organizer's, which proves staff membership and
does not. The split is the same one the content correction makes, for the same reason —
the organizer is the person the files end up with when the form did not catch them, and
that happens precisely after the deadline has passed.

What the applicant's side deliberately does *not* ask is whether the entry is editable:
the files outlive the rest of the entry on purpose, so that a festival whose
registration closed on Monday still takes the backing track on Friday. The one thing
that closes them early is the organizer's freeze, which every applicant path here
checks for exactly that reason.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    AttachFileCommand,
    RemoveAttachmentByOrganizerCommand,
    RemoveAttachmentCommand,
    UploadAttachmentByOrganizerCommand,
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
    OrganizationReadModel,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.value_objects import AttachmentId, AttachmentType, FileReference

from ._support import (
    ensure_editing_unlocked,
    ensure_owner,
    ensure_reviewer,
    load_submission,
    parse_reviewer_id,
    parse_submission_id,
    parse_user_id,
    try_resubmit_after_correction_edit,
)

__all__ = [
    "AttachFileHandler",
    "RemoveAttachmentByOrganizerHandler",
    "RemoveAttachmentHandler",
    "UploadAttachmentByOrganizerHandler",
    "UploadAttachmentHandler",
]


def _parse_attachment_type(raw: str) -> AttachmentType:
    try:
        return AttachmentType(raw)
    except ValueError as exc:
        raise InvalidInputError("Неизвестный тип файла.") from exc


class AttachFileHandler:
    """Use case: attach a file reference to the submission."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: AttachFileCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        ensure_editing_unlocked(catalog=self._catalog, competition_id=submission.competition_id)

        try:
            attachment_type = AttachmentType(command.attachment_type)
        except ValueError as exc:
            raise InvalidInputError("Неизвестный тип файла.") from exc
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
    """Use case: remove an attachment reference from the submission.

    Takes the festival's freeze into account and nothing else about the calendar: a
    file may be taken off for as long as it may be replaced, and an applicant who can
    upload but not delete is an applicant with two tracks and no way to say which one
    is the right one.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock
        self._events = events

    def handle(self, command: RemoveAttachmentCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_owner(submission, parse_user_id(command.requested_by))
        ensure_editing_unlocked(catalog=self._catalog, competition_id=submission.competition_id)
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

        # Before the deadline question, because the freeze closes the window too and
        # «срок истёк» would be a lie about a date that has not arrived.
        ensure_editing_unlocked(catalog=self._catalog, competition_id=submission.competition_id)
        if not self._catalog.accepts_upload(competition_id=submission.competition_id, attachment_kind=attachment_type.value, now=now):
            raise DeadlinePassedError("Срок загрузки файлов этого типа истёк.")

        performance = submission.performance
        participation_format_id = performance.participation_format_id.json() if performance is not None else None
        constraints = self._upload_policy.limits_for(
            competition_id=submission.competition_id,
            attachment_kind=attachment_type.value,
            participation_format_id=participation_format_id,
        )
        incoming = len(command.content)
        # A shared ceiling is measured against what is already attached: media is one
        # budget over a performance's photographs and video, so the question is not "is
        # this file too big" but "does it still fit".
        already = submission.attached_bytes(constraints.shared_budget_kinds) if constraints.shared_budget_kinds else 0
        if already + incoming > constraints.max_bytes:
            raise FileTooLargeError(
                f"Файлы этого типа занимают не больше {constraints.max_bytes // (1024 * 1024)} МБ суммарно — "
                f"сейчас загружено {already // (1024 * 1024)} МБ и добавляется ещё {incoming // (1024 * 1024)} МБ."
            )
        extension = PurePosixPath(command.filename).suffix.lstrip(".").lower()
        if not constraints.allows_extension(extension):
            raise UnsupportedFileTypeError(f"Файлы «{extension or 'без расширения'}» для этого типа загрузки не принимаются.")

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
                size_bytes=incoming,
            )
        domain_events += try_resubmit_after_correction_edit(submission=submission, catalog=self._catalog, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class UploadAttachmentByOrganizerHandler:
    """Use case: attach an uploaded file to an entry on the applicant's behalf.

    The organizer's copy of :class:`UploadAttachmentHandler`, and it differs in exactly
    two places.

    * **Authority.** Staff membership instead of ownership — the organizer is editing
      somebody else's entry, which is what the whole correction path is for.
    * **No upload deadline.** The applicant's path refuses a file once the window for
      that kind has closed. The organizer's must not: the usual reason a phonogram is
      being uploaded here is that it arrived by message or on a flash drive *after*
      the window closed, and refusing it would leave the sound desk without a track
      that is sitting in the organizer's inbox.

    Everything else is deliberately identical. The size ceiling and the allowed
    extensions still apply, because those are not calendar rules — they are what the
    storage can hold and what the hall can play, and they are the same file either way.
    Nor does this path resubmit a returned entry: the organizer decides where the entry
    stands, so a file they add leaves its status exactly where they put it.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
        storage: FileStorage,
        upload_policy: CompetitionUploadPolicy,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._organization = organization
        self._storage = storage
        self._upload_policy = upload_policy
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: UploadAttachmentByOrganizerCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_reviewer(self._organization, parse_reviewer_id(command.reviewer_id))
        attachment_type = _parse_attachment_type(command.attachment_type)

        performance = submission.performance
        participation_format_id = performance.participation_format_id.json() if performance is not None else None
        constraints = self._upload_policy.limits_for(
            competition_id=submission.competition_id,
            attachment_kind=attachment_type.value,
            participation_format_id=participation_format_id,
        )
        incoming = len(command.content)
        already = submission.attached_bytes(constraints.shared_budget_kinds) if constraints.shared_budget_kinds else 0
        if already + incoming > constraints.max_bytes:
            raise FileTooLargeError(
                f"Файлы этого типа занимают не больше {constraints.max_bytes // (1024 * 1024)} МБ суммарно — "
                f"сейчас загружено {already // (1024 * 1024)} МБ и добавляется ещё {incoming // (1024 * 1024)} МБ."
            )
        extension = PurePosixPath(command.filename).suffix.lstrip(".").lower()
        if not constraints.allows_extension(extension):
            raise UnsupportedFileTypeError(f"Файлы «{extension or 'без расширения'}» для этого типа загрузки не принимаются.")

        reference = self._storage.save(content=command.content, filename=command.filename, content_type=command.content_type)
        attachment_id = AttachmentId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            domain_events = submission.add_attachment(
                attachment_id=attachment_id,
                attachment_type=attachment_type,
                file=FileReference(reference),
                now=now,
                caption=command.caption,
                size_bytes=incoming,
            )
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class RemoveAttachmentByOrganizerHandler:
    """Use case: take a file off an entry on the applicant's behalf (organizer).

    The counterpart of :class:`UploadAttachmentByOrganizerHandler`, and needed for the
    same reason an upload is: an organizer who can only ever add files cannot replace a
    track sent to them twice, and a wrong one left in place is what gets played.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._organization = organization
        self._clock = clock
        self._events = events

    def handle(self, command: RemoveAttachmentByOrganizerCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_reviewer(self._organization, parse_reviewer_id(command.reviewer_id))
        with translate_domain_errors():
            attachment_id = AttachmentId.from_string(command.attachment_id)
            domain_events = submission.remove_attachment(attachment_id=attachment_id, now=now)
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))
