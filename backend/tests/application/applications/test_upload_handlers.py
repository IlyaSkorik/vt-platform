"""Handler tests for the upload-attachment use case, against in-memory fakes."""

from __future__ import annotations

import pytest

from apps.applications.application.commands.attachments import UploadAttachmentHandler
from apps.applications.application.dto.commands import UploadAttachmentCommand
from apps.applications.application.exceptions import (
    CompetitionClosedError,
    DeadlinePassedError,
    FileTooLargeError,
    SubmissionNotFoundError,
    UnsupportedFileTypeError,
)
from apps.applications.domain.entities import Performance, Submission
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    CompetitionId,
    DisciplineId,
    Duration,
    NominationId,
    ParticipantGroupId,
    ParticipationFormatId,
    PerformanceTitle,
    SubmissionId,
    UserId,
)

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


def _draft_submission(applicant: UserId, *, nomination: NominationId | None = None) -> Submission:
    submission, _ = Submission.draft(
        submission_id=SubmissionId.generate(),
        competition_id=CompetitionId.from_uuid(SubmissionId.generate().value),
        applicant_id=applicant,
        now=NOW,
    )
    if nomination is not None:
        # The freeze is a genre's, so an entry only runs into one once it names a genre.
        submission.set_performance(
            performance=Performance(
                title=PerformanceTitle("Swan Lake"),
                duration=Duration.of(minutes=3),
                nomination_id=nomination,
                discipline_id=DisciplineId.from_uuid(SubmissionId.generate().value),
                age_category_id=AgeCategoryId.from_uuid(SubmissionId.generate().value),
                participant_group_id=ParticipantGroupId.from_uuid(SubmissionId.generate().value),
                participation_format_id=ParticipationFormatId.from_uuid(SubmissionId.generate().value),
            ),
            now=NOW,
        )
    return submission


class _Env:
    def __init__(
        self,
        *,
        policy: FakeCompetitionUploadPolicy | None = None,
        accepts_upload: bool = True,
        locked_nominations: frozenset[str] = frozenset(),
    ) -> None:
        self.submissions = FakeSubmissionRepository()
        self.storage = FakeFileStorage()
        self.policy = policy or FakeCompetitionUploadPolicy()
        self.catalog = FakeCompetitionCatalog(accepts_upload=accepts_upload, locked_nominations=locked_nominations)
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


def test_upload_refused_once_the_organizer_froze_the_genre() -> None:
    """Замок закрывает и загрузку — иначе он закрывал бы всё, кроме главного.

    Сроки загрузки переживают закрытие приёма специально, так что без отдельной
    проверки кнопка «закрыть редактирование» оставляла бы файлы жанра открытыми
    ровно до их собственного дедлайна.
    """
    applicant = UserId.from_uuid(SubmissionId.generate().value)
    nomination = NominationId.from_uuid(SubmissionId.generate().value)
    env = _Env(locked_nominations=frozenset({nomination.json()}))
    submission = _draft_submission(applicant, nomination=nomination)
    env.submissions.save(submission)

    with pytest.raises(CompetitionClosedError) as refusal:
        env.handler.handle(_command(submission.id.json(), applicant.json()))

    # Не «срок истёк»: срок может быть ещё через неделю, это решение организатора.
    assert "организатор" in str(refusal.value).lower()
    assert env.storage.saved == {}


def test_a_frozen_genre_does_not_close_the_uploads_of_another() -> None:
    """Ради этого замок и переехал на жанр: вокал печатают, хореография ещё грузит."""
    applicant = UserId.from_uuid(SubmissionId.generate().value)
    frozen = NominationId.from_uuid(SubmissionId.generate().value)
    env = _Env(locked_nominations=frozenset({frozen.json()}))
    submission = _draft_submission(applicant, nomination=NominationId.from_uuid(SubmissionId.generate().value))
    env.submissions.save(submission)

    env.handler.handle(_command(submission.id.json(), applicant.json()))

    assert env.storage.saved != {}


def test_upload_unknown_submission_is_not_found() -> None:
    env = _Env()
    with pytest.raises(SubmissionNotFoundError):
        env.handler.handle(_command(SubmissionId.generate().json(), uuid7_str()))


def test_media_files_share_one_size_budget() -> None:
    """Photographs and video count together, which is the whole point of the change.

    A performance normally arrives as several files. A per-file limit either waves ten of
    them through or refuses one legitimate one; what the organizer is protecting is their
    storage and the applicant's connection, and both care about the sum.
    """
    applicant = UserId.from_uuid(SubmissionId.generate().value)
    env = _Env(
        policy=FakeCompetitionUploadPolicy(
            max_bytes=100,
            allowed_extensions=frozenset({"mp4", "jpg"}),
            shared_budget_kinds=frozenset({"VIDEO", "IMAGE"}),
        )
    )
    submission = _draft_submission(applicant)
    env.submissions.save(submission)

    env.handler.handle(_command(submission.id.json(), applicant.json(), filename="clip.mp4", content=b"x" * 60, attachment_type="VIDEO"))
    # 60 already attached, and a photograph of 30 still fits.
    env.handler.handle(_command(submission.id.json(), applicant.json(), filename="photo.jpg", content=b"y" * 30, attachment_type="IMAGE"))

    # 90 attached: a second photograph of 30 does not, even though 30 is far below the
    # ceiling on its own.
    with pytest.raises(FileTooLargeError):
        env.handler.handle(_command(submission.id.json(), applicant.json(), filename="photo2.jpg", content=b"z" * 30, attachment_type="IMAGE"))
    assert len(env.storage.saved) == 2


def test_a_per_file_limit_ignores_what_is_already_attached() -> None:
    # Music has no shared budget, so two tracks of 60 against a 100-byte per-file limit are
    # both fine — the change must not quietly turn every limit into a total.
    applicant = UserId.from_uuid(SubmissionId.generate().value)
    env = _Env(policy=FakeCompetitionUploadPolicy(max_bytes=100, allowed_extensions=frozenset({"mp3"})))
    submission = _draft_submission(applicant)
    env.submissions.save(submission)

    env.handler.handle(_command(submission.id.json(), applicant.json(), filename="a.mp3", content=b"x" * 60))
    env.handler.handle(_command(submission.id.json(), applicant.json(), filename="b.mp3", content=b"y" * 60))

    assert len(env.storage.saved) == 2
