"""Unit tests for the Submission aggregate root and its child entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from apps.applications.domain.entities import Submission
from apps.applications.domain.events import (
    AttachmentAdded,
    ParticipantAdded,
    PerformanceDefined,
    PriceSnapshotCreated,
    ReviewAdded,
    SubmissionCancelled,
    SubmissionCreated,
    SubmissionReturnedForCorrection,
    SubmissionSubmitted,
)
from apps.applications.domain.exceptions import (
    CannotRemoveLastParticipantError,
    CombinationNotAdmissibleError,
    DirectConstructionError,
    DuplicateAttachmentError,
    DuplicateParticipantError,
    IllegalStatusTransitionError,
    InvalidBirthDateError,
    ParticipantCountMismatchError,
    ParticipantNotFoundError,
    ParticipantRequiredError,
    PerformanceRequiredError,
    PriceSnapshotLockedError,
    PriceSnapshotRequiredError,
    SubmissionNotEditableError,
)
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    AttachmentId,
    AttachmentType,
    BirthDate,
    CompetitionId,
    DisciplineId,
    Duration,
    FileReference,
    Gender,
    Money,
    NominationId,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipantId,
    ParticipationFormatId,
    Performance,
    PerformanceTitle,
    PersonName,
    PriceSnapshot,
    ReviewComment,
    ReviewerId,
    ReviewId,
    SubmissionId,
    SubmissionParticipationPolicy,
    SubmissionStatus,
    TeacherId,
    TeacherRole,
    UserId,
)

NOW = datetime(2026, 7, 10, tzinfo=UTC)


def _new_id() -> uuid.UUID:
    return SubmissionId.generate().value


def _performance() -> Performance:
    return Performance(
        title=PerformanceTitle("Swan Lake"),
        duration=Duration.of(minutes=3, seconds=30),
        nomination_id=NominationId.from_uuid(_new_id()),
        discipline_id=DisciplineId.from_uuid(_new_id()),
        age_category_id=AgeCategoryId.from_uuid(_new_id()),
        participant_group_id=ParticipantGroupId.from_uuid(_new_id()),
        participation_format_id=ParticipationFormatId.from_uuid(_new_id()),
    )


def _draft() -> Submission:
    submission, _ = Submission.draft(
        submission_id=SubmissionId.generate(),
        competition_id=CompetitionId.from_uuid(_new_id()),
        applicant_id=UserId.from_uuid(_new_id()),
        now=NOW,
    )
    return submission


def _person(first: str = "Anna", last: str = "Ivanova") -> PersonName:
    return PersonName(first_name=first, last_name=last)


@dataclass
class SoloFixture:
    submission: Submission
    solo_policy: SubmissionParticipationPolicy


def _solo_ready() -> SoloFixture:
    """A DRAFT submission with a performance, one participant and a frozen price."""
    s = _draft()
    s.set_performance(performance=_performance(), now=NOW)
    s.add_participant(
        participant_id=ParticipantId.generate(),
        name=_person(),
        birth_date=BirthDate(date(2012, 5, 1)),
        gender=Gender.FEMALE,
        now=NOW,
    )
    s.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("1500"), calculated_at=NOW), now=NOW)
    policy = SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(1, 1))
    return SoloFixture(s, policy)


class TestConstruction:
    def test_direct_construction_refused(self) -> None:
        with pytest.raises(DirectConstructionError):
            Submission(
                _token=object(),
                _id=SubmissionId.generate(),
                _competition_id=CompetitionId.from_uuid(_new_id()),
                _applicant_id=UserId.from_uuid(_new_id()),
                _status=SubmissionStatus.DRAFT,
                _created_at=NOW,
                _updated_at=NOW,
            )

    def test_draft_starts_empty_and_emits_created(self) -> None:
        submission, events = Submission.draft(
            submission_id=SubmissionId.generate(),
            competition_id=CompetitionId.from_uuid(_new_id()),
            applicant_id=UserId.from_uuid(_new_id()),
            now=NOW,
        )
        assert submission.is_draft()
        assert submission.performance is None
        assert submission.participant_count == 0
        assert [type(e).__name__ for e in events] == ["SubmissionCreated"]
        assert isinstance(events[0], SubmissionCreated)

    def test_draft_with_performance_emits_performance_defined(self) -> None:
        _submission, events = Submission.draft(
            submission_id=SubmissionId.generate(),
            competition_id=CompetitionId.from_uuid(_new_id()),
            applicant_id=UserId.from_uuid(_new_id()),
            now=NOW,
            performance=_performance(),
        )
        assert [type(e).__name__ for e in events] == ["SubmissionCreated", "PerformanceDefined"]

    def test_rehydrate_reconstructs_without_events(self) -> None:
        fx = _solo_ready()
        original = fx.submission
        restored = Submission.rehydrate(
            submission_id=original.id,
            competition_id=original.competition_id,
            applicant_id=original.applicant_id,
            status=original.status,
            created_at=original.created_at,
            updated_at=original.updated_at,
            performance=original.performance,
            participants=original.participants,
            price_snapshot=original.price_snapshot,
            version=original.version,
        )
        assert restored == original
        assert restored.participant_count == 1
        assert restored.version == original.version


class TestContentEditing:
    def test_set_performance_emits_event(self) -> None:
        s = _draft()
        events = s.set_performance(performance=_performance(), now=NOW)
        assert isinstance(events[0], PerformanceDefined)
        assert s.performance is not None

    def test_duplicate_participant_rejected(self) -> None:
        s = _draft()
        name, bd = _person(), BirthDate(date(2012, 5, 1))
        s.add_participant(participant_id=ParticipantId.generate(), name=name, birth_date=bd, gender=Gender.FEMALE, now=NOW)
        with pytest.raises(DuplicateParticipantError):
            s.add_participant(participant_id=ParticipantId.generate(), name=name, birth_date=bd, gender=Gender.FEMALE, now=NOW)

    def test_future_birth_date_rejected(self) -> None:
        s = _draft()
        with pytest.raises(InvalidBirthDateError):
            s.add_participant(
                participant_id=ParticipantId.generate(),
                name=_person(),
                birth_date=BirthDate(date(2030, 1, 1)),
                gender=Gender.MALE,
                now=NOW,
            )

    def test_add_participant_emits_event(self) -> None:
        s = _draft()
        events = s.add_participant(
            participant_id=ParticipantId.generate(), name=_person(), birth_date=BirthDate(date(2012, 5, 1)), gender=Gender.FEMALE, now=NOW
        )
        assert isinstance(events[0], ParticipantAdded)

    def test_cannot_remove_last_participant(self) -> None:
        s = _draft()
        pid = ParticipantId.generate()
        s.add_participant(participant_id=pid, name=_person(), birth_date=BirthDate(date(2012, 5, 1)), gender=Gender.FEMALE, now=NOW)
        with pytest.raises(CannotRemoveLastParticipantError):
            s.remove_participant(participant_id=pid, now=NOW)

    def test_remove_participant_when_more_than_one(self) -> None:
        s = _draft()
        keep = ParticipantId.generate()
        drop = ParticipantId.generate()
        s.add_participant(participant_id=keep, name=_person("Anna"), birth_date=BirthDate(date(2012, 5, 1)), gender=Gender.FEMALE, now=NOW)
        s.add_participant(participant_id=drop, name=_person("Boris"), birth_date=BirthDate(date(2011, 3, 2)), gender=Gender.MALE, now=NOW)
        s.remove_participant(participant_id=drop, now=NOW)
        assert s.participant_count == 1

    def test_remove_missing_participant_raises(self) -> None:
        s = _draft()
        with pytest.raises(ParticipantNotFoundError):
            s.remove_participant(participant_id=ParticipantId.generate(), now=NOW)

    def test_teacher_add_and_remove(self) -> None:
        s = _draft()
        tid = TeacherId.generate()
        s.add_teacher(teacher_id=tid, name=_person("Olga", "Petrova"), role=TeacherRole("Choreographer"), now=NOW)
        assert len(s.teachers) == 1
        s.remove_teacher(teacher_id=tid, now=NOW)
        assert len(s.teachers) == 0

    def test_duplicate_attachment_rejected(self) -> None:
        s = _draft()
        file = FileReference("s3://music.mp3")
        s.add_attachment(attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.MUSIC, file=file, now=NOW)
        with pytest.raises(DuplicateAttachmentError):
            s.add_attachment(attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.MUSIC, file=file, now=NOW)

    def test_add_attachment_emits_event(self) -> None:
        s = _draft()
        events = s.add_attachment(
            attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.VIDEO, file=FileReference("s3://v.mp4"), now=NOW
        )
        assert isinstance(events[0], AttachmentAdded)

    def test_editing_blocked_after_submit(self) -> None:
        fx = _solo_ready()
        fx.submission.submit(policy=fx.solo_policy, now=NOW)
        with pytest.raises(SubmissionNotEditableError):
            fx.submission.add_participant(
                participant_id=ParticipantId.generate(), name=_person("New"), birth_date=BirthDate(date(2013, 1, 1)), gender=Gender.MALE, now=NOW
            )


class TestPriceSnapshot:
    def test_set_emits_event(self) -> None:
        s = _draft()
        events = s.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("900"), calculated_at=NOW), now=NOW)
        assert isinstance(events[0], PriceSnapshotCreated)
        assert s.price_snapshot is not None

    def test_recompute_allowed_while_draft(self) -> None:
        s = _draft()
        s.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("900"), calculated_at=NOW), now=NOW)
        s.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("1200"), calculated_at=NOW), now=NOW)
        assert s.price_snapshot is not None
        assert s.price_snapshot.amount == Money.of("1200").amount

    def test_frozen_after_submit(self) -> None:
        fx = _solo_ready()
        fx.submission.submit(policy=fx.solo_policy, now=NOW)
        with pytest.raises(PriceSnapshotLockedError):
            fx.submission.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("1"), calculated_at=NOW), now=NOW)


class TestSubmitInvariants:
    def test_requires_performance(self) -> None:
        s = _draft()
        s.add_participant(
            participant_id=ParticipantId.generate(), name=_person(), birth_date=BirthDate(date(2012, 5, 1)), gender=Gender.FEMALE, now=NOW
        )
        s.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("1500"), calculated_at=NOW), now=NOW)
        policy = SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(1, 1))
        with pytest.raises(PerformanceRequiredError):
            s.submit(policy=policy, now=NOW)

    def test_requires_participant(self) -> None:
        s = _draft()
        s.set_performance(performance=_performance(), now=NOW)
        s.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("1500"), calculated_at=NOW), now=NOW)
        policy = SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(1, 1))
        with pytest.raises(ParticipantRequiredError):
            s.submit(policy=policy, now=NOW)

    def test_requires_price_snapshot(self) -> None:
        s = _draft()
        s.set_performance(performance=_performance(), now=NOW)
        s.add_participant(
            participant_id=ParticipantId.generate(), name=_person(), birth_date=BirthDate(date(2012, 5, 1)), gender=Gender.FEMALE, now=NOW
        )
        policy = SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(1, 1))
        with pytest.raises(PriceSnapshotRequiredError):
            s.submit(policy=policy, now=NOW)

    def test_rejects_inadmissible_combination(self) -> None:
        fx = _solo_ready()
        policy = SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(1, 1), is_admissible=False)
        with pytest.raises(CombinationNotAdmissibleError):
            fx.submission.submit(policy=policy, now=NOW)

    def test_participant_count_must_match_group(self) -> None:
        fx = _solo_ready()
        duet_policy = SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(2, 2))
        with pytest.raises(ParticipantCountMismatchError):
            fx.submission.submit(policy=duet_policy, now=NOW)

    def test_successful_submit_transitions_and_emits(self) -> None:
        fx = _solo_ready()
        events = fx.submission.submit(policy=fx.solo_policy, now=NOW)
        assert fx.submission.status is SubmissionStatus.SUBMITTED
        assert isinstance(events[0], SubmissionSubmitted)
        assert events[0].previous_status is SubmissionStatus.DRAFT


class TestLifecycle:
    def test_happy_path_to_completed(self) -> None:
        fx = _solo_ready()
        s = fx.submission
        s.submit(policy=fx.solo_policy, now=NOW)
        s.begin_review(now=NOW)
        s.approve(now=NOW)
        s.await_payment(now=NOW)
        s.mark_paid(now=NOW)
        s.accept(now=NOW)
        s.schedule(now=NOW)
        s.complete(now=NOW)
        assert s.status is SubmissionStatus.COMPLETED

    def test_illegal_transition_rejected(self) -> None:
        fx = _solo_ready()
        with pytest.raises(IllegalStatusTransitionError):
            fx.submission.approve(now=NOW)  # cannot approve a DRAFT

    def test_return_for_correction_records_review_and_reopens(self) -> None:
        fx = _solo_ready()
        s = fx.submission
        s.submit(policy=fx.solo_policy, now=NOW)
        s.begin_review(now=NOW)
        events = s.return_for_correction(
            review_id=ReviewId.generate(),
            reviewer_id=ReviewerId.from_uuid(_new_id()),
            comment=ReviewComment("Please re-upload the music."),
            now=NOW,
        )
        assert s.status is SubmissionStatus.REQUIRES_CORRECTION
        assert s.is_editable()
        assert len(s.reviews) == 1
        assert [type(e).__name__ for e in events] == ["ReviewAdded", "SubmissionReturnedForCorrection"]
        assert isinstance(events[1], SubmissionReturnedForCorrection)

    def test_resubmit_after_correction(self) -> None:
        fx = _solo_ready()
        s = fx.submission
        s.submit(policy=fx.solo_policy, now=NOW)
        s.begin_review(now=NOW)
        s.return_for_correction(review_id=ReviewId.generate(), reviewer_id=ReviewerId.from_uuid(_new_id()), comment=ReviewComment("fix"), now=NOW)
        events = s.submit(policy=fx.solo_policy, now=NOW)
        assert s.status is SubmissionStatus.SUBMITTED
        assert isinstance(events[0], SubmissionSubmitted)
        assert events[0].previous_status is SubmissionStatus.REQUIRES_CORRECTION

    def test_multiple_review_iterations(self) -> None:
        fx = _solo_ready()
        s = fx.submission
        s.submit(policy=fx.solo_policy, now=NOW)
        s.begin_review(now=NOW)
        events = s.add_review(
            review_id=ReviewId.generate(), reviewer_id=ReviewerId.from_uuid(_new_id()), comment=ReviewComment("looks good so far"), now=NOW
        )
        s.add_review(review_id=ReviewId.generate(), reviewer_id=ReviewerId.from_uuid(_new_id()), comment=ReviewComment("second pass"), now=NOW)
        assert isinstance(events[0], ReviewAdded)
        assert len(s.reviews) == 2

    def test_review_rejected_outside_review_states(self) -> None:
        fx = _solo_ready()
        with pytest.raises(IllegalStatusTransitionError):
            fx.submission.add_review(
                review_id=ReviewId.generate(), reviewer_id=ReviewerId.from_uuid(_new_id()), comment=ReviewComment("too early"), now=NOW
            )

    def test_cancel_before_accept(self) -> None:
        fx = _solo_ready()
        s = fx.submission
        s.submit(policy=fx.solo_policy, now=NOW)
        events = s.cancel(now=NOW)
        assert s.status is SubmissionStatus.CANCELLED
        assert isinstance(events[0], SubmissionCancelled)
        assert events[0].previous_status is SubmissionStatus.SUBMITTED

    def test_cannot_cancel_after_accept(self) -> None:
        fx = _solo_ready()
        s = fx.submission
        s.submit(policy=fx.solo_policy, now=NOW)
        s.begin_review(now=NOW)
        s.approve(now=NOW)
        s.await_payment(now=NOW)
        s.mark_paid(now=NOW)
        s.accept(now=NOW)
        with pytest.raises(IllegalStatusTransitionError):
            s.cancel(now=NOW)


class TestConcurrencyAndIdentity:
    def test_version_bumps_on_mutation(self) -> None:
        s = _draft()
        before = s.version
        s.set_performance(performance=_performance(), now=NOW)
        assert s.version == before + 1

    def test_equality_by_id(self) -> None:
        fx = _solo_ready()
        same = Submission.rehydrate(
            submission_id=fx.submission.id,
            competition_id=fx.submission.competition_id,
            applicant_id=fx.submission.applicant_id,
            status=SubmissionStatus.DRAFT,
            created_at=NOW,
            updated_at=NOW,
        )
        assert same == fx.submission
        assert hash(same) == hash(fx.submission)
