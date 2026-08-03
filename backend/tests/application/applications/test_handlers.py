"""Tests for the Applications (Competition Submission) application use cases.

Drives the command and query handlers over in-memory fakes, exercising the full
lifecycle (create -> content -> price -> submit -> review -> approve -> payment ->
accept) plus the application-owned guards (ownership, organizer authorization,
cross-context existence) and the domain-error translation.
"""

from __future__ import annotations

import pytest

from apps.applications.application.commands import (
    AcceptSubmissionHandler,
    AddParticipantHandler,
    AddTeacherHandler,
    ApproveSubmissionHandler,
    AttachFileHandler,
    CalculatePriceHandler,
    CancelSubmissionHandler,
    CreateSubmissionHandler,
    DeleteDraftSubmissionHandler,
    MarkPaidHandler,
    MarkWaitingPaymentHandler,
    RemoveParticipantHandler,
    ReturnSubmissionForCorrectionHandler,
    SetPerformanceHandler,
    StartReviewHandler,
    SubmitSubmissionHandler,
    UpdateParticipantHandler,
)
from apps.applications.application.dto.commands import (
    AcceptSubmissionCommand,
    AddParticipantCommand,
    AddTeacherCommand,
    ApproveSubmissionCommand,
    AttachFileCommand,
    CalculatePriceCommand,
    CancelSubmissionCommand,
    CreateSubmissionCommand,
    DeleteDraftSubmissionCommand,
    MarkPaidCommand,
    MarkWaitingPaymentCommand,
    RemoveParticipantCommand,
    ReturnSubmissionForCorrectionCommand,
    SetPerformanceCommand,
    StartReviewCommand,
    SubmitSubmissionCommand,
    UpdateParticipantCommand,
)
from apps.applications.application.dto.queries import (
    GetSubmissionHistoryQuery,
    GetSubmissionQuery,
    ListCompetitionSubmissionsQuery,
    ListMySubmissionsQuery,
)
from apps.applications.application.exceptions import (
    ApplicantNotFoundError,
    CompetitionClosedError,
    CompetitionCombinationNotFoundError,
    CompetitionNotFoundError,
    DuplicateChildError,
    PermissionDeniedError,
    SubmissionInvariantViolationError,
    SubmissionNotFoundError,
    SubmissionStateConflictError,
)
from apps.applications.application.queries import (
    GetSubmissionHandler,
    GetSubmissionHistoryHandler,
    ListCompetitionSubmissionsHandler,
    ListMySubmissionsHandler,
)
from apps.applications.domain.value_objects import Money, PriceCalculationType, SubmissionStatus

from .fakes import (
    FakeClock,
    FakeCompetitionCatalog,
    FakeIdentityReadModel,
    FakeOrganizationReadModel,
    FakeSubmissionRepository,
    RecordingEventPublisher,
    SequenceUuidGenerator,
    uuid7_str,
)


class Env:
    """A bundle of freshly wired fakes shared by a single test."""

    def __init__(
        self,
        *,
        catalog: FakeCompetitionCatalog | None = None,
        organization: FakeOrganizationReadModel | None = None,
        identity: FakeIdentityReadModel | None = None,
    ) -> None:
        self.submissions = FakeSubmissionRepository()
        self.catalog = catalog if catalog is not None else FakeCompetitionCatalog()
        self.organization = organization if organization is not None else FakeOrganizationReadModel()
        self.identity = identity if identity is not None else FakeIdentityReadModel()
        self.clock = FakeClock()
        self.uuids = SequenceUuidGenerator()
        self.events = RecordingEventPublisher()

    # -- command handler factories ------------------------------------------

    def create(self) -> CreateSubmissionHandler:
        return CreateSubmissionHandler(
            submissions=self.submissions,
            catalog=self.catalog,
            identity=self.identity,
            clock=self.clock,
            uuids=self.uuids,
            events=self.events,
        )

    def set_performance(self) -> SetPerformanceHandler:
        return SetPerformanceHandler(submissions=self.submissions, catalog=self.catalog, clock=self.clock, events=self.events)

    def add_participant(self) -> AddParticipantHandler:
        return AddParticipantHandler(submissions=self.submissions, catalog=self.catalog, clock=self.clock, uuids=self.uuids, events=self.events)

    def update_participant(self) -> UpdateParticipantHandler:
        return UpdateParticipantHandler(submissions=self.submissions, catalog=self.catalog, clock=self.clock, uuids=self.uuids, events=self.events)

    def remove_participant(self) -> RemoveParticipantHandler:
        return RemoveParticipantHandler(submissions=self.submissions, catalog=self.catalog, clock=self.clock, events=self.events)

    def add_teacher(self) -> AddTeacherHandler:
        return AddTeacherHandler(submissions=self.submissions, catalog=self.catalog, clock=self.clock, uuids=self.uuids, events=self.events)

    def attach_file(self) -> AttachFileHandler:
        return AttachFileHandler(submissions=self.submissions, clock=self.clock, uuids=self.uuids, events=self.events)

    def calculate_price(self) -> CalculatePriceHandler:
        return CalculatePriceHandler(submissions=self.submissions, catalog=self.catalog, clock=self.clock, events=self.events)

    def submit(self) -> SubmitSubmissionHandler:
        return SubmitSubmissionHandler(submissions=self.submissions, catalog=self.catalog, clock=self.clock, events=self.events)

    def start_review(self) -> StartReviewHandler:
        return StartReviewHandler(submissions=self.submissions, organization=self.organization, clock=self.clock, events=self.events)

    def return_for_correction(self) -> ReturnSubmissionForCorrectionHandler:
        return ReturnSubmissionForCorrectionHandler(
            submissions=self.submissions,
            organization=self.organization,
            clock=self.clock,
            uuids=self.uuids,
            events=self.events,
        )

    def approve(self) -> ApproveSubmissionHandler:
        return ApproveSubmissionHandler(submissions=self.submissions, organization=self.organization, clock=self.clock, events=self.events)

    def mark_waiting_payment(self) -> MarkWaitingPaymentHandler:
        return MarkWaitingPaymentHandler(submissions=self.submissions, organization=self.organization, clock=self.clock, events=self.events)

    def mark_paid(self) -> MarkPaidHandler:
        return MarkPaidHandler(submissions=self.submissions, organization=self.organization, clock=self.clock, events=self.events)

    def accept(self) -> AcceptSubmissionHandler:
        return AcceptSubmissionHandler(submissions=self.submissions, organization=self.organization, clock=self.clock, events=self.events)

    def cancel(self) -> CancelSubmissionHandler:
        return CancelSubmissionHandler(submissions=self.submissions, clock=self.clock, events=self.events)

    def delete_draft(self) -> DeleteDraftSubmissionHandler:
        return DeleteDraftSubmissionHandler(submissions=self.submissions)

    # -- query handler factories --------------------------------------------

    def get_submission(self) -> GetSubmissionHandler:
        return GetSubmissionHandler(submissions=self.submissions, organization=self.organization)

    def get_history(self) -> GetSubmissionHistoryHandler:
        return GetSubmissionHistoryHandler(submissions=self.submissions, organization=self.organization)

    def list_mine(self) -> ListMySubmissionsHandler:
        return ListMySubmissionsHandler(submissions=self.submissions)

    def list_competition(self) -> ListCompetitionSubmissionsHandler:
        return ListCompetitionSubmissionsHandler(submissions=self.submissions, organization=self.organization)


def _create(env: Env, *, competition_id: str, applicant_id: str) -> str:
    """Create a draft and return its id."""
    result = env.create().handle(CreateSubmissionCommand(competition_id=competition_id, applicant_id=applicant_id))
    return result.submission.id


def _set_performance(env: Env, *, submission_id: str, owner: str) -> None:
    env.set_performance().handle(
        SetPerformanceCommand(
            submission_id=submission_id,
            requested_by=owner,
            title="Winter Sonata",
            duration_seconds=180,
            nomination_id=uuid7_str(),
            discipline_id=uuid7_str(),
            age_category_id=uuid7_str(),
            participant_group_id=uuid7_str(),
            participation_format_id=uuid7_str(),
        )
    )


def _add_participant(env: Env, *, submission_id: str, owner: str, first: str = "Anna", birth: str = "2005-04-01") -> str:
    result = env.add_participant().handle(
        AddParticipantCommand(
            submission_id=submission_id,
            requested_by=owner,
            first_name=first,
            last_name="Ivanova",
            birth_date=birth,
            gender="FEMALE",
        )
    )
    return result.submission.participants[-1].id


def _reach_draft_ready(env: Env, *, competition_id: str, owner: str) -> str:
    """Create a fully priced, submittable draft and return its id."""
    submission_id = _create(env, competition_id=competition_id, applicant_id=owner)
    _set_performance(env, submission_id=submission_id, owner=owner)
    _add_participant(env, submission_id=submission_id, owner=owner)
    env.calculate_price().handle(CalculatePriceCommand(submission_id=submission_id, requested_by=owner))
    return submission_id


class TestCreateSubmission:
    def test_creates_draft_and_publishes_event(self) -> None:
        env = Env()
        competition_id, applicant_id = uuid7_str(), uuid7_str()

        result = env.create().handle(CreateSubmissionCommand(competition_id=competition_id, applicant_id=applicant_id))

        assert result.submission.status == SubmissionStatus.DRAFT.value
        assert result.submission.competition_id == competition_id
        assert result.submission.applicant_id == applicant_id
        assert len(env.submissions.saved) == 1
        assert [type(e).__name__ for e in env.events.published] == ["SubmissionCreated"]

    def test_unknown_applicant_is_rejected(self) -> None:
        env = Env(identity=FakeIdentityReadModel(known=False))
        with pytest.raises(ApplicantNotFoundError):
            env.create().handle(CreateSubmissionCommand(competition_id=uuid7_str(), applicant_id=uuid7_str()))

    def test_unknown_competition_is_rejected(self) -> None:
        env = Env(catalog=FakeCompetitionCatalog(known=False))
        with pytest.raises(CompetitionNotFoundError):
            env.create().handle(CreateSubmissionCommand(competition_id=uuid7_str(), applicant_id=uuid7_str()))

    def test_closed_competition_is_rejected(self) -> None:
        env = Env(catalog=FakeCompetitionCatalog(open_for_submissions=False))
        with pytest.raises(CompetitionClosedError):
            env.create().handle(CreateSubmissionCommand(competition_id=uuid7_str(), applicant_id=uuid7_str()))


class TestContentEditing:
    def test_owner_can_build_content(self) -> None:
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)

        _set_performance(env, submission_id=submission_id, owner=owner)
        _add_participant(env, submission_id=submission_id, owner=owner)
        result = env.add_teacher().handle(
            AddTeacherCommand(
                submission_id=submission_id,
                requested_by=owner,
                first_name="Boris",
                last_name="Petrov",
                role="Concertmaster",
            )
        )
        assert result.submission.performance is not None
        assert len(result.submission.participants) == 1
        assert len(result.submission.teachers) == 1

    def test_non_owner_is_denied(self) -> None:
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        with pytest.raises(PermissionDeniedError):
            _set_performance(env, submission_id=submission_id, owner=uuid7_str())

    def test_attach_file(self) -> None:
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        result = env.attach_file().handle(
            AttachFileCommand(
                submission_id=submission_id,
                requested_by=owner,
                attachment_type="MUSIC",
                file_reference="s3://bucket/track.mp3",
            )
        )
        assert len(result.submission.attachments) == 1
        assert result.submission.attachments[0].type == "MUSIC"

    def test_duplicate_participant_translated(self) -> None:
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        _add_participant(env, submission_id=submission_id, owner=owner, first="Anna", birth="2005-04-01")
        with pytest.raises(DuplicateChildError):
            _add_participant(env, submission_id=submission_id, owner=owner, first="Anna", birth="2005-04-01")

    def test_update_participant_replaces_with_new_identity(self) -> None:
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        original_id = _add_participant(env, submission_id=submission_id, owner=owner, first="Ana")

        result = env.update_participant().handle(
            UpdateParticipantCommand(
                submission_id=submission_id,
                requested_by=owner,
                participant_id=original_id,
                first_name="Anna",
                last_name="Ivanova",
                birth_date="2005-04-01",
                gender="FEMALE",
            )
        )
        assert len(result.submission.participants) == 1
        replacement = result.submission.participants[0]
        assert replacement.first_name == "Anna"
        assert replacement.id != original_id

    def test_remove_last_participant_leaves_draft_empty(self) -> None:
        # Removing the sole participant is allowed while DRAFT so it can be swapped;
        # submit re-enforces the "at least one participant" invariant.
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        participant_id = _add_participant(env, submission_id=submission_id, owner=owner)
        result = env.remove_participant().handle(
            RemoveParticipantCommand(submission_id=submission_id, requested_by=owner, participant_id=participant_id)
        )
        assert len(result.submission.participants) == 0


class TestPricing:
    def test_price_is_per_participant_times_count(self) -> None:
        env = Env(catalog=FakeCompetitionCatalog(price=Money.of("300.00")))
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        _set_performance(env, submission_id=submission_id, owner=owner)
        _add_participant(env, submission_id=submission_id, owner=owner, first="Anna")
        _add_participant(env, submission_id=submission_id, owner=owner, first="Bella")

        result = env.calculate_price().handle(CalculatePriceCommand(submission_id=submission_id, requested_by=owner))

        assert result.submission.price is not None
        assert result.submission.price.amount == "600.00"

    def test_price_counts_collective_member_headcount(self) -> None:
        # A collective is a single entry carrying its headcount; per-participant
        # pricing bills the whole ensemble (8 x 300.00), not one line.
        env = Env(catalog=FakeCompetitionCatalog(price=Money.of("300.00")))
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        _set_performance(env, submission_id=submission_id, owner=owner)
        env.add_participant().handle(
            AddParticipantCommand(
                submission_id=submission_id,
                requested_by=owner,
                display_name="Choir Aurora",
                member_count=8,
            )
        )
        result = env.calculate_price().handle(CalculatePriceCommand(submission_id=submission_id, requested_by=owner))
        assert result.submission.price is not None
        assert result.submission.price.amount == "2400.00"

    def test_price_is_fixed_for_per_performance(self) -> None:
        env = Env(
            catalog=FakeCompetitionCatalog(
                price=Money.of("300.00"),
                calculation_type=PriceCalculationType.PER_PERFORMANCE,
            )
        )
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        _set_performance(env, submission_id=submission_id, owner=owner)
        _add_participant(env, submission_id=submission_id, owner=owner, first="Anna")
        _add_participant(env, submission_id=submission_id, owner=owner, first="Bella")

        result = env.calculate_price().handle(CalculatePriceCommand(submission_id=submission_id, requested_by=owner))

        assert result.submission.price is not None
        assert result.submission.price.amount == "300.00"

    def test_price_without_performance_is_rejected(self) -> None:
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        with pytest.raises(SubmissionStateConflictError):
            env.calculate_price().handle(CalculatePriceCommand(submission_id=submission_id, requested_by=owner))

    def test_missing_combination_price_is_rejected(self) -> None:
        env = Env()
        # The catalog reports no price for this combination.
        env.catalog.price = None
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        _set_performance(env, submission_id=submission_id, owner=owner)
        with pytest.raises(CompetitionCombinationNotFoundError):
            env.calculate_price().handle(CalculatePriceCommand(submission_id=submission_id, requested_by=owner))


class TestLifecycle:
    def test_full_happy_path(self) -> None:
        env = Env()
        owner, competition_id = uuid7_str(), uuid7_str()
        reviewer = uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)

        env.submit().handle(SubmitSubmissionCommand(submission_id=submission_id, requested_by=owner))
        env.start_review().handle(StartReviewCommand(submission_id=submission_id, reviewer_id=reviewer))
        env.approve().handle(ApproveSubmissionCommand(submission_id=submission_id, reviewer_id=reviewer))
        env.mark_waiting_payment().handle(MarkWaitingPaymentCommand(submission_id=submission_id, reviewer_id=reviewer))
        env.mark_paid().handle(MarkPaidCommand(submission_id=submission_id, reviewer_id=reviewer))
        result = env.accept().handle(AcceptSubmissionCommand(submission_id=submission_id, reviewer_id=reviewer))

        assert result.submission.status == SubmissionStatus.ACCEPTED.value

    def test_submit_requires_price(self) -> None:
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        _set_performance(env, submission_id=submission_id, owner=owner)
        _add_participant(env, submission_id=submission_id, owner=owner)
        with pytest.raises(SubmissionInvariantViolationError):
            env.submit().handle(SubmitSubmissionCommand(submission_id=submission_id, requested_by=owner))

    def test_submit_into_closed_competition_is_rejected(self) -> None:
        env = Env()
        owner, competition_id = uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        env.catalog.open_for_submissions = False
        with pytest.raises(CompetitionClosedError):
            env.submit().handle(SubmitSubmissionCommand(submission_id=submission_id, requested_by=owner))

    def test_return_for_correction_records_review_and_reopens(self) -> None:
        env = Env()
        owner, reviewer, competition_id = uuid7_str(), uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        env.submit().handle(SubmitSubmissionCommand(submission_id=submission_id, requested_by=owner))
        env.start_review().handle(StartReviewCommand(submission_id=submission_id, reviewer_id=reviewer))

        result = env.return_for_correction().handle(
            ReturnSubmissionForCorrectionCommand(submission_id=submission_id, reviewer_id=reviewer, comment="Please fix the title.")
        )
        assert result.submission.status == SubmissionStatus.REQUIRES_CORRECTION.value
        assert len(result.submission.reviews) == 1

    def test_unauthorized_reviewer_is_denied(self) -> None:
        env = Env(organization=FakeOrganizationReadModel(reviewer=False))
        owner, competition_id = uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        env.submit().handle(SubmitSubmissionCommand(submission_id=submission_id, requested_by=owner))
        with pytest.raises(PermissionDeniedError):
            env.start_review().handle(StartReviewCommand(submission_id=submission_id, reviewer_id=uuid7_str()))

    def test_illegal_transition_is_translated(self) -> None:
        env = Env()
        owner, reviewer, competition_id = uuid7_str(), uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        env.submit().handle(SubmitSubmissionCommand(submission_id=submission_id, requested_by=owner))
        # Approve is illegal directly from SUBMITTED (review has not begun).
        with pytest.raises(SubmissionStateConflictError):
            env.approve().handle(ApproveSubmissionCommand(submission_id=submission_id, reviewer_id=reviewer))

    def test_cancel_by_owner(self) -> None:
        env = Env()
        owner, competition_id = uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        result = env.cancel().handle(CancelSubmissionCommand(submission_id=submission_id, requested_by=owner))
        assert result.submission.status == SubmissionStatus.CANCELLED.value


class TestDeleteDraft:
    def test_owner_deletes_draft(self) -> None:
        env = Env()
        owner = uuid7_str()
        submission_id = _create(env, competition_id=uuid7_str(), applicant_id=owner)
        env.delete_draft().handle(DeleteDraftSubmissionCommand(submission_id=submission_id, requested_by=owner))
        assert len(env.submissions.deleted) == 1
        assert not env.submissions.exists(env.submissions.deleted[0])

    def test_cannot_delete_submitted(self) -> None:
        env = Env()
        owner, competition_id = uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        env.submit().handle(SubmitSubmissionCommand(submission_id=submission_id, requested_by=owner))
        with pytest.raises(SubmissionStateConflictError):
            env.delete_draft().handle(DeleteDraftSubmissionCommand(submission_id=submission_id, requested_by=owner))

    def test_unknown_submission_is_not_found(self) -> None:
        env = Env()
        with pytest.raises(SubmissionNotFoundError):
            env.delete_draft().handle(DeleteDraftSubmissionCommand(submission_id=uuid7_str(), requested_by=uuid7_str()))


class TestQueries:
    def test_get_submission_by_owner(self) -> None:
        env = Env()
        owner, competition_id = uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        view = env.get_submission().handle(GetSubmissionQuery(submission_id=submission_id, requested_by=owner))
        assert view.id == submission_id
        assert view.price is not None

    def test_get_submission_by_reviewer(self) -> None:
        env = Env()
        owner, competition_id = uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        view = env.get_submission().handle(GetSubmissionQuery(submission_id=submission_id, requested_by=uuid7_str()))
        assert view.id == submission_id

    def test_get_submission_denied_for_stranger(self) -> None:
        env = Env(organization=FakeOrganizationReadModel(reviewer=False))
        owner, competition_id = uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        with pytest.raises(PermissionDeniedError):
            env.get_submission().handle(GetSubmissionQuery(submission_id=submission_id, requested_by=uuid7_str()))

    def test_list_my_submissions(self) -> None:
        env = Env()
        owner, other = uuid7_str(), uuid7_str()
        _create(env, competition_id=uuid7_str(), applicant_id=owner)
        _create(env, competition_id=uuid7_str(), applicant_id=owner)
        _create(env, competition_id=uuid7_str(), applicant_id=other)
        mine = env.list_mine().handle(ListMySubmissionsQuery(applicant_id=owner))
        assert len(mine) == 2
        assert all(s.applicant_id == owner for s in mine)

    def test_list_competition_submissions_requires_reviewer(self) -> None:
        env = Env(organization=FakeOrganizationReadModel(reviewer=False))
        competition_id = uuid7_str()
        _create(env, competition_id=competition_id, applicant_id=uuid7_str())
        with pytest.raises(PermissionDeniedError):
            env.list_competition().handle(ListCompetitionSubmissionsQuery(competition_id=competition_id, requested_by=uuid7_str()))

    def test_list_competition_submissions_for_reviewer(self) -> None:
        env = Env()
        competition_id = uuid7_str()
        _create(env, competition_id=competition_id, applicant_id=uuid7_str())
        _create(env, competition_id=competition_id, applicant_id=uuid7_str())
        listed = env.list_competition().handle(ListCompetitionSubmissionsQuery(competition_id=competition_id, requested_by=uuid7_str()))
        assert len(listed) == 2

    def test_get_history_returns_reviews(self) -> None:
        env = Env()
        owner, reviewer, competition_id = uuid7_str(), uuid7_str(), uuid7_str()
        submission_id = _reach_draft_ready(env, competition_id=competition_id, owner=owner)
        env.submit().handle(SubmitSubmissionCommand(submission_id=submission_id, requested_by=owner))
        env.start_review().handle(StartReviewCommand(submission_id=submission_id, reviewer_id=reviewer))
        env.return_for_correction().handle(ReturnSubmissionForCorrectionCommand(submission_id=submission_id, reviewer_id=reviewer, comment="Fix it."))
        history = env.get_history().handle(GetSubmissionHistoryQuery(submission_id=submission_id, requested_by=owner))
        assert history.current_status == SubmissionStatus.REQUIRES_CORRECTION.value
        assert len(history.reviews) == 1
        assert history.reviews[0].comment == "Fix it."
