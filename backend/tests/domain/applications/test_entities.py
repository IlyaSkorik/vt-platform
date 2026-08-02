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
    CombinationNotAdmissibleError,
    DirectConstructionError,
    DuplicateAttachmentError,
    DuplicateParticipantError,
    IllegalStatusTransitionError,
    InvalidBirthDateError,
    InvalidParticipantMemberCountError,
    InvalidPersonNameError,
    ParticipantCountMismatchError,
    ParticipantNotFoundError,
    ParticipantRequiredError,
    PerformanceRequiredError,
    PriceSnapshotLockedError,
    PriceSnapshotRequiredError,
    RequiredAttachmentMissingError,
    SubmissionNotEditableError,
    TeacherRequiredError,
)
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    AttachmentId,
    AttachmentType,
    BirthDate,
    CompetitionId,
    DirectoryTeacherId,
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
    RegistryParticipantId,
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


def _accepted() -> Submission:
    """A submission walked all the way to ACCEPTED — committed to the running order."""
    fx = _solo_ready()
    s = fx.submission
    s.submit(policy=fx.solo_policy, now=NOW)
    s.begin_review(now=NOW)
    s.approve(now=NOW)
    s.await_payment(now=NOW)
    s.mark_paid(now=NOW)
    s.accept(now=NOW)
    return s


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

    def test_remove_last_participant_leaves_draft_empty(self) -> None:
        # A DRAFT may be left without participants so the sole one can be swapped;
        # the "at least one participant" rule is enforced only at submit time.
        s = _draft()
        pid = ParticipantId.generate()
        s.add_participant(participant_id=pid, name=_person(), birth_date=BirthDate(date(2012, 5, 1)), gender=Gender.FEMALE, now=NOW)
        s.remove_participant(participant_id=pid, now=NOW)
        assert s.participant_count == 0

    def test_collective_member_count_drives_participant_count(self) -> None:
        # One collective entry with a headcount counts as that many participants.
        s = _draft()
        s.add_participant(participant_id=ParticipantId.generate(), display_name="Choir Aurora", member_count=8, now=NOW)
        assert s.participant_count == 8
        assert s.participants[0].member_count == 8

    def test_member_count_must_be_a_positive_integer(self) -> None:
        s = _draft()
        with pytest.raises(InvalidParticipantMemberCountError):
            s.add_participant(participant_id=ParticipantId.generate(), display_name="Choir", member_count=0, now=NOW)

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

    def test_several_music_files_may_ride_on_one_submission(self) -> None:
        """An act performed to more than one track brings more than one file."""
        s = _draft()
        for name in ("s3://intro.mp3", "s3://main.mp3", "s3://finale.mp3"):
            s.add_attachment(attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.MUSIC, file=FileReference(name), now=NOW)
        assert [a.file.value for a in s.attachments] == ["s3://intro.mp3", "s3://main.mp3", "s3://finale.mp3"]

    def test_music_still_attachable_once_the_entry_is_accepted(self) -> None:
        """The state a running order is built from is the state a track is wanted in."""
        s = _accepted()
        s.add_attachment(
            attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.MUSIC, file=FileReference("s3://late.mp3"), now=NOW
        )
        assert [a.type for a in s.attachments] == [AttachmentType.MUSIC]

    def test_music_still_attachable_once_the_entry_is_scheduled(self) -> None:
        s = _accepted()
        s.schedule(now=NOW)
        s.add_attachment(
            attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.MUSIC, file=FileReference("s3://late.mp3"), now=NOW
        )
        assert len(s.attachments) == 1

    def test_an_accepted_entry_can_have_its_track_replaced(self) -> None:
        s = _accepted()
        attachment_id = AttachmentId.generate()
        s.add_attachment(attachment_id=attachment_id, attachment_type=AttachmentType.MUSIC, file=FileReference("s3://wrong.mp3"), now=NOW)
        s.remove_attachment(attachment_id=attachment_id, now=NOW)
        s.add_attachment(
            attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.MUSIC, file=FileReference("s3://right.mp3"), now=NOW
        )
        assert [a.file.value for a in s.attachments] == ["s3://right.mp3"]

    def test_music_is_refused_once_the_performance_took_place(self) -> None:
        s = _accepted()
        s.schedule(now=NOW)
        s.complete(now=NOW)
        with pytest.raises(SubmissionNotEditableError):
            s.add_attachment(
                attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.MUSIC, file=FileReference("s3://late.mp3"), now=NOW
            )

    def test_other_attachment_kinds_stay_frozen_with_the_content(self) -> None:
        """Only the backing track outlives the freeze: paperwork is a claim about the entry."""
        s = _accepted()
        with pytest.raises(SubmissionNotEditableError):
            s.add_attachment(
                attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.DOCUMENT, file=FileReference("s3://doc.pdf"), now=NOW
            )

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
        """The applicant's own withdrawal stops at the running order."""
        s = _accepted()
        with pytest.raises(IllegalStatusTransitionError):
            s.cancel(now=NOW)

    def test_applicant_cannot_cancel_once_scheduled(self) -> None:
        s = _accepted()
        s.schedule(now=NOW)
        with pytest.raises(IllegalStatusTransitionError):
            s.cancel(now=NOW)

    def test_organizer_can_cancel_an_accepted_submission(self) -> None:
        """Committed to the running order, but a withdrawal is still the organizer's
        call — a disqualification or a request granted as an exception."""
        s = _accepted()

        events = s.cancel_by_organizer(now=NOW)

        assert s.status is SubmissionStatus.CANCELLED
        assert isinstance(events[0], SubmissionCancelled)
        assert events[0].previous_status is SubmissionStatus.ACCEPTED

    def test_organizer_can_cancel_a_scheduled_submission(self) -> None:
        s = _accepted()
        s.schedule(now=NOW)

        events = s.cancel_by_organizer(now=NOW)

        assert s.status is SubmissionStatus.CANCELLED
        assert events[0].previous_status is SubmissionStatus.SCHEDULED

    def test_not_even_the_organizer_can_cancel_a_performed_submission(self) -> None:
        """COMPLETED stays terminal: the performance happened, and its diploma may
        already be in the register."""
        s = _accepted()
        s.schedule(now=NOW)
        s.complete(now=NOW)

        with pytest.raises(IllegalStatusTransitionError):
            s.cancel_by_organizer(now=NOW)

    def test_organizer_cancellation_before_the_running_order_works_the_same(self) -> None:
        fx = _solo_ready()
        s = fx.submission
        s.submit(policy=fx.solo_policy, now=NOW)

        events = s.cancel_by_organizer(now=NOW)

        assert s.status is SubmissionStatus.CANCELLED
        assert events[0].previous_status is SubmissionStatus.SUBMITTED


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


class TestRegistryLinkedParticipants:
    """The submission participant is a Participant Registry snapshot (solo or collective)."""

    def test_solo_registry_participant_carries_link_and_snapshot(self) -> None:
        submission = _draft()
        registry_id = RegistryParticipantId.from_uuid(_new_id())
        submission.add_participant(
            participant_id=ParticipantId.generate(),
            name=_person("Sofia", "Petrova"),
            birth_date=BirthDate(date(2013, 3, 4)),
            gender=Gender.FEMALE,
            registry_participant_id=registry_id,
            now=NOW,
        )
        participant = submission.participants[0]
        assert participant.registry_participant_id == registry_id
        assert participant.display_name == "Petrova Sofia"
        assert participant.gender is Gender.FEMALE

    def test_collective_has_display_name_only(self) -> None:
        submission = _draft()
        submission.add_participant(
            participant_id=ParticipantId.generate(),
            display_name='Ensemble "Constellation"',
            registry_participant_id=RegistryParticipantId.from_uuid(_new_id()),
            now=NOW,
        )
        participant = submission.participants[0]
        assert participant.display_name == 'Ensemble "Constellation"'
        assert participant.name is None
        assert participant.birth_date is None
        assert participant.gender is None

    def test_other_gender_is_accepted(self) -> None:
        submission = _draft()
        submission.add_participant(
            participant_id=ParticipantId.generate(),
            name=_person(),
            birth_date=BirthDate(date(2012, 1, 1)),
            gender=Gender.OTHER,
            now=NOW,
        )
        assert submission.participants[0].gender is Gender.OTHER

    def test_same_registry_participant_cannot_be_added_twice(self) -> None:
        submission = _draft()
        registry_id = RegistryParticipantId.from_uuid(_new_id())
        submission.add_participant(
            participant_id=ParticipantId.generate(),
            display_name="Sofia",
            registry_participant_id=registry_id,
            now=NOW,
        )
        with pytest.raises(DuplicateParticipantError):
            submission.add_participant(
                participant_id=ParticipantId.generate(),
                display_name="Sofia (again)",
                registry_participant_id=registry_id,
                now=NOW,
            )

    def test_collective_requires_a_display_name(self) -> None:
        submission = _draft()
        with pytest.raises(InvalidPersonNameError):
            submission.add_participant(
                participant_id=ParticipantId.generate(),
                registry_participant_id=RegistryParticipantId.from_uuid(_new_id()),
                now=NOW,
            )


class TestDirectoryLinkedTeachers:
    """A credited teacher links to the Teacher Directory and keeps a name/role snapshot."""

    def test_teacher_carries_directory_link_and_snapshot(self) -> None:
        submission = _draft()
        directory_id = DirectoryTeacherId.from_uuid(_new_id())
        submission.add_teacher(
            teacher_id=TeacherId.generate(),
            name=_person("Elena", "Sokolova"),
            role=TeacherRole("Choreographer"),
            directory_teacher_id=directory_id,
            now=NOW,
        )
        teacher = submission.teachers[0]
        assert teacher.directory_teacher_id == directory_id
        assert teacher.name.full_name == "Sokolova Elena"
        assert teacher.role == TeacherRole("Choreographer")

    def test_manual_teacher_has_no_directory_link(self) -> None:
        submission = _draft()
        submission.add_teacher(
            teacher_id=TeacherId.generate(),
            name=_person("Elena", "Sokolova"),
            role=TeacherRole("Teacher"),
            now=NOW,
        )
        assert submission.teachers[0].directory_teacher_id is None


def _policy(**flags: bool) -> SubmissionParticipationPolicy:
    return SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(1, 1), **flags)


class TestSubmitRequirements:
    """Submit enforces the competition-configured requirements carried on the policy."""

    def test_requires_teacher_when_policy_requires(self) -> None:
        submission = _solo_ready().submission
        with pytest.raises(TeacherRequiredError):
            submission.submit(policy=_policy(requires_teacher=True), now=NOW)

    def test_credited_teacher_satisfies_requirement(self) -> None:
        submission = _solo_ready().submission
        submission.add_teacher(teacher_id=TeacherId.generate(), name=_person("Elena", "Sokolova"), role=TeacherRole("Teacher"), now=NOW)
        submission.submit(policy=_policy(requires_teacher=True), now=NOW)
        assert submission.status is SubmissionStatus.SUBMITTED

    def test_requires_music_upload(self) -> None:
        submission = _solo_ready().submission
        with pytest.raises(RequiredAttachmentMissingError):
            submission.submit(policy=_policy(requires_music=True), now=NOW)

    def test_music_attachment_satisfies_requirement(self) -> None:
        submission = _solo_ready().submission
        submission.add_attachment(
            attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.MUSIC, file=FileReference("s3://music.mp3"), now=NOW
        )
        submission.submit(policy=_policy(requires_music=True), now=NOW)
        assert submission.status is SubmissionStatus.SUBMITTED

    def test_requires_video_file(self) -> None:
        submission = _solo_ready().submission
        with pytest.raises(RequiredAttachmentMissingError):
            submission.submit(policy=_policy(requires_video_file=True), now=NOW)

    def test_requires_document(self) -> None:
        submission = _solo_ready().submission
        with pytest.raises(RequiredAttachmentMissingError):
            submission.submit(policy=_policy(requires_document=True), now=NOW)

    def test_document_attachment_satisfies_requirement(self) -> None:
        submission = _solo_ready().submission
        submission.add_attachment(
            attachment_id=AttachmentId.generate(), attachment_type=AttachmentType.DOCUMENT, file=FileReference("s3://document.pdf"), now=NOW
        )
        submission.submit(policy=_policy(requires_document=True), now=NOW)
        assert submission.status is SubmissionStatus.SUBMITTED
