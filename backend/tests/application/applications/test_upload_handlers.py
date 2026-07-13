"""Handler tests for the upload-attachment use case, against in-memory fakes."""

from __future__ import annotations

import pytest

from apps.applications.application.commands.attachments import UploadAttachmentHandler
from apps.applications.application.dto.commands import UploadAttachmentCommand
from apps.applications.application.exceptions import (
    DeadlinePassedError,
    FileTooLargeError,
    SubmissionNotFoundError,
    UnsupportedFileTypeError,
)
from apps.applications.domain.entities import Submission
from apps.applications.domain.value_objects import CompetitionId, SubmissionId, UserId

from .fakes import (
    NOW,
    FakeClock,
    FakeCompetitionCatalog,
    FakeCompetitionUploadPolicy,
    FakeFileStorage,
    FakeSubmissionRepository,
    RecordingEventPublisher,
    SequenceUuidGenerator,
    uuid7_str,
)


def _draft_submission(applicant: UserId) -> Submission:
    submission, _ = Submission.draft(
        submission_id=SubmissionId.generate(),
        competition_id=CompetitionId.from_uuid(SubmissionId.generate().value),
        applicant_id=applicant,
        now=NOW,
    )
    return submission


class _Env:
    def __init__(self, *, policy: FakeCompetitionUploadPolicy | None = None, accepts_upload: bool = True) -> None:
        self.submissions = FakeSubmissionRepository()
        self.storage = FakeFileStorage()
        self.policy = policy or FakeCompetitionUploadPolicy()
        self.catalog = FakeCompetitionCatalog(accepts_upload=accepts_upload)
        self.handler = UploadAttachmentHandler(
            submissions=self.submissions,
            storage=self.storage,
            upload_policy=self.policy,
            catalog=self.catalog,
            clock=FakeClock(),
            uuids=SequenceUuidGenerator(),
            events=RecordingEventPublisher(),
        )


def _command(
    submission_id: str, applicant: str, *, filename: str = "track.mp3", content: bytes = b"x" * 10, attachment_type: str = "MUSIC"
) -> UploadAttachmentCommand:
    return UploadAttachmentCommand(
        submission_id=submission_id,
        requested_by=applicant,
        attachment_type=attachment_type,
        filename=filename,
        content_type="audio/mpeg",
        content=content,
        caption="Backing track",
    )


def test_upload_stores_and_attaches() -> None:
    applicant = UserId.from_uuid(SubmissionId.generate().value)
    env = _Env()
    submission = _draft_submission(applicant)
    env.submissions.save(submission)
    result = env.handler.handle(_command(submission.id.json(), applicant.json()))
    assert len(result.submission.attachments) == 1
    assert result.submission.attachments[0].type == "MUSIC"
    assert len(env.storage.saved) == 1


def test_upload_rejects_oversized_file() -> None:
    applicant = UserId.from_uuid(SubmissionId.generate().value)
    env = _Env(policy=FakeCompetitionUploadPolicy(max_bytes=5))
    submission = _draft_submission(applicant)
    env.submissions.save(submission)
    with pytest.raises(FileTooLargeError):
        env.handler.handle(_command(submission.id.json(), applicant.json(), content=b"x" * 100))
    assert env.storage.saved == {}


def test_upload_rejects_unsupported_extension() -> None:
    applicant = UserId.from_uuid(SubmissionId.generate().value)
    env = _Env(policy=FakeCompetitionUploadPolicy(allowed_extensions=frozenset({"mp3"})))
    submission = _draft_submission(applicant)
    env.submissions.save(submission)
    with pytest.raises(UnsupportedFileTypeError):
        env.handler.handle(_command(submission.id.json(), applicant.json(), filename="virus.exe"))
    assert env.storage.saved == {}


def test_upload_rejected_after_upload_deadline() -> None:
    applicant = UserId.from_uuid(SubmissionId.generate().value)
    env = _Env(accepts_upload=False)
    submission = _draft_submission(applicant)
    env.submissions.save(submission)
    with pytest.raises(DeadlinePassedError):
        env.handler.handle(_command(submission.id.json(), applicant.json()))
    assert env.storage.saved == {}


def test_upload_unknown_submission_is_not_found() -> None:
    env = _Env()
    with pytest.raises(SubmissionNotFoundError):
        env.handler.handle(_command(SubmissionId.generate().json(), uuid7_str()))
