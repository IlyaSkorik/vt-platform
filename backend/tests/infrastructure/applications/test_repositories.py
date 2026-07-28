"""Round-trip tests for the Applications persistence adapters (real PostgreSQL).

Build an aggregate through the domain, persist it, reload it, and assert the whole
graph survives the JSON-backed mapping unchanged. Also cover optimistic-concurrency
conflict detection on ``save``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    ApplicationId,
    AttachmentId,
    AttachmentType,
    BirthDate,
    CompetitionId,
    Consent,
    DisciplineId,
    Duration,
    EducationalOrganizationId,
    FileReference,
    Gender,
    Money,
    NominationId,
    OrganizationName,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipantId,
    ParticipationFormatId,
    Performance,
    PerformanceTitle,
    PersonName,
    PriceSnapshot,
    ServiceId,
    ServiceLine,
    SubmissionId,
    SubmissionParticipationPolicy,
    TeacherId,
    TeacherRole,
    UserId,
)
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.applications.infrastructure.repositories import (
    ConcurrencyConflictError,
    DjangoApplicationRepository,
    DjangoSubmissionRepository,
)

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def _build_submission() -> Submission:
    submission, _ = Submission.draft(
        submission_id=SubmissionId.generate(),
        competition_id=CompetitionId.from_uuid(SubmissionId.generate().value),
        applicant_id=UserId.from_uuid(SubmissionId.generate().value),
        now=NOW,
    )
    submission.set_performance(
        performance=Performance(
            title=PerformanceTitle("Swan Lake"),
            duration=Duration.of(minutes=3, seconds=30),
            nomination_id=NominationId.from_uuid(SubmissionId.generate().value),
            discipline_id=DisciplineId.from_uuid(SubmissionId.generate().value),
            age_category_id=AgeCategoryId.from_uuid(SubmissionId.generate().value),
            participant_group_id=ParticipantGroupId.from_uuid(SubmissionId.generate().value),
            participation_format_id=ParticipationFormatId.from_uuid(SubmissionId.generate().value),
            comment="Выход с точки 3. Нужен микрофон на стойке.",
        ),
        now=NOW,
    )
    submission.add_participant(
        participant_id=ParticipantId.from_uuid(SubmissionId.generate().value),
        name=PersonName(first_name="Anna", last_name="Ivanova", middle_name="Petrovna"),
        birth_date=BirthDate(date(2014, 5, 1)),
        gender=Gender.FEMALE,
        now=NOW,
    )
    submission.add_teacher(
        teacher_id=TeacherId.from_uuid(SubmissionId.generate().value),
        name=PersonName(first_name="Olga", last_name="Petrova"),
        role=TeacherRole("Choreographer"),
        now=NOW,
    )
    submission.add_attachment(
        attachment_id=AttachmentId.from_uuid(SubmissionId.generate().value),
        attachment_type=AttachmentType.MUSIC,
        file=FileReference("s3://bucket/music.mp3"),
        caption="Backing track",
        now=NOW,
    )
    submission.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("300.00"), calculated_at=NOW), now=NOW)
    return submission


class TestSubmissionRepository:
    def test_round_trip_preserves_graph(self) -> None:
        repo = DjangoSubmissionRepository()
        original = _build_submission()
        repo.save(original)

        loaded = repo.get(original.id)
        assert loaded is not None
        assert loaded.id == original.id
        assert loaded.competition_id == original.competition_id
        assert loaded.applicant_id == original.applicant_id
        assert loaded.status is original.status
        assert loaded.version == original.version
        assert loaded.performance == original.performance
        assert loaded.participants == original.participants
        assert loaded.teachers == original.teachers
        assert loaded.attachments == original.attachments
        assert loaded.price_snapshot == original.price_snapshot
        assert loaded.performance is not None
        assert loaded.performance.comment == "Выход с точки 3. Нужен микрофон на стойке."

    def test_rows_written_before_the_comment_existed_load_with_a_blank_one(self) -> None:
        """The performance is stored as JSON, so older rows simply have no key."""
        repo = DjangoSubmissionRepository()
        submission = _build_submission()
        repo.save(submission)
        row = SubmissionModel.objects.get(id=submission.id.value)
        del row.performance["comment"]
        row.save(update_fields=["performance"])

        loaded = repo.get(submission.id)
        assert loaded is not None
        assert loaded.performance is not None
        assert loaded.performance.comment == ""

    def test_update_and_list(self) -> None:
        repo = DjangoSubmissionRepository()
        submission = _build_submission()
        repo.save(submission)
        submission.add_participant(
            participant_id=ParticipantId.from_uuid(SubmissionId.generate().value),
            name=PersonName(first_name="Boris", last_name="Sidorov"),
            birth_date=BirthDate(date(2013, 2, 2)),
            gender=Gender.MALE,
            now=NOW,
        )
        repo.save(submission)

        assert repo.exists(submission.id)
        by_applicant = repo.list_by_applicant(submission.applicant_id)
        assert [s.id for s in by_applicant] == [submission.id]
        assert by_applicant[0].participant_count == 2

    def test_concurrency_conflict(self) -> None:
        repo = DjangoSubmissionRepository()
        submission = _build_submission()
        repo.save(submission)
        first = repo.get(submission.id)
        second = repo.get(submission.id)
        assert first is not None and second is not None

        first.add_teacher(
            teacher_id=TeacherId.from_uuid(SubmissionId.generate().value),
            name=PersonName(first_name="A", last_name="B"),
            role=TeacherRole("Teacher"),
            now=NOW,
        )
        repo.save(first)
        second.add_teacher(
            teacher_id=TeacherId.from_uuid(SubmissionId.generate().value),
            name=PersonName(first_name="C", last_name="D"),
            role=TeacherRole("Teacher"),
            now=NOW,
        )
        with pytest.raises(ConcurrencyConflictError):
            repo.save(second)

    def test_submit_then_reload_keeps_status_and_reviews(self) -> None:
        repo = DjangoSubmissionRepository()
        submission = _build_submission()
        submission.submit(policy=SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(min_count=1)), now=NOW)
        repo.save(submission)
        loaded = repo.get(submission.id)
        assert loaded is not None
        assert loaded.status.value == "SUBMITTED"


def _build_application() -> Application:
    application, _ = Application.create(
        application_id=ApplicationId.generate(),
        competition_id=CompetitionId.from_uuid(SubmissionId.generate().value),
        applicant_id=UserId.from_uuid(SubmissionId.generate().value),
        now=NOW,
    )
    application.select_educational_organization(
        educational_organization_id=EducationalOrganizationId.from_uuid(SubmissionId.generate().value),
        organization_name=OrganizationName("Music School No.1"),
        now=NOW,
    )
    submission = _build_submission()
    from apps.applications.application.orders._support import ref_from_submission

    application.attach_submission(ref=ref_from_submission(submission), now=NOW)
    application.add_service(
        service_line=ServiceLine(
            service_id=ServiceId.from_uuid(SubmissionId.generate().value), name="T-shirt", unit_price=Money.of("25.00"), quantity=2
        ),
        now=NOW,
    )
    application.record_consents(consents=[Consent(code="personal_data", version="v1", accepted_at=NOW)], now=NOW)
    return application


class TestApplicationRepository:
    def test_round_trip_preserves_graph(self) -> None:
        repo = DjangoApplicationRepository()
        original = _build_application()
        repo.save(original)

        loaded = repo.get(original.id)
        assert loaded is not None
        assert loaded.id == original.id
        assert loaded.status is original.status
        assert loaded.organization_name == original.organization_name
        assert loaded.educational_organization_id == original.educational_organization_id
        assert loaded.submission_refs == original.submission_refs
        assert loaded.service_lines == original.service_lines
        assert loaded.consents == original.consents
        assert loaded.total_price == original.total_price
        assert len(loaded.status_history) == len(original.status_history)
        assert loaded.version == original.version

    def test_list_by_applicant(self) -> None:
        repo = DjangoApplicationRepository()
        application = _build_application()
        repo.save(application)
        listed = repo.list_by_applicant(application.applicant_id)
        assert [a.id for a in listed] == [application.id]

    def test_concurrency_conflict(self) -> None:
        repo = DjangoApplicationRepository()
        application = _build_application()
        repo.save(application)
        first = repo.get(application.id)
        second = repo.get(application.id)
        assert first is not None and second is not None
        first.record_consents(consents=[Consent(code="media", version="v1", accepted_at=NOW)], now=NOW)
        repo.save(first)
        second.record_consents(consents=[Consent(code="other", version="v1", accepted_at=NOW)], now=NOW)
        with pytest.raises(ConcurrencyConflictError):
            repo.save(second)

    def test_many_mutations_in_one_unit_of_work_save_without_false_conflict(self) -> None:
        """Regression: submitting an order bumps the version several times before one
        save (refresh refs + submit); the optimistic-concurrency pre-image must be the
        loaded version, not ``version - 1``."""
        repo = DjangoApplicationRepository()
        application = _build_application()
        repo.save(application)
        loaded = repo.get(application.id)
        assert loaded is not None
        base_version = loaded.version

        loaded.add_service(
            service_line=ServiceLine(
                service_id=ServiceId.from_uuid(SubmissionId.generate().value), name="Badge", unit_price=Money.of("5.00"), quantity=1
            ),
            now=NOW,
        )
        loaded.record_consents(consents=[Consent(code="media", version="v1", accepted_at=NOW)], now=NOW)
        loaded.submit(now=NOW)
        assert loaded.version >= base_version + 2  # several bumps before one save

        repo.save(loaded)  # must not raise ConcurrencyConflictError

        reloaded = repo.get(application.id)
        assert reloaded is not None
        assert reloaded.status.value == "SUBMITTED"
        assert reloaded.version == loaded.version
