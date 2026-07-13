"""Handler tests for the Application (order) use cases, against in-memory fakes.

These exercise the order orchestration over the two aggregates: the Application
(order) and the existing Submission. Where a flow depends on submissions being
built or reviewed, the test drives the Submission aggregate directly (that is a
separate workflow with its own endpoints) and then invokes the order use case.
"""

from __future__ import annotations

from datetime import date

import pytest

from apps.applications.application.dto.order_commands import (
    AddSubmissionToApplicationCommand,
    CancelApplicationCommand,
    ConsentInput,
    CreateApplicationCommand,
    MarkApplicationPaidCommand,
    RecordConsentsCommand,
    RemoveSubmissionFromApplicationCommand,
    RequestApplicationPaymentCommand,
    SelectAdditionalServiceCommand,
    SelectEducationalOrganizationCommand,
    SubmitApplicationCommand,
)
from apps.applications.application.dto.queries import (
    GetApplicationQuery,
    ListApplicationsQuery,
    ListDraftApplicationsQuery,
)
from apps.applications.application.exceptions import (
    AdditionalServiceNotAvailableError,
    AdditionalServiceNotFoundError,
    ApplicantNotFoundError,
    ApplicationInvariantViolationError,
    CompetitionClosedError,
    CompetitionNotFoundError,
    DeadlinePassedError,
    EducationalOrganizationNotFoundError,
    PermissionDeniedError,
)
from apps.applications.application.orders import (
    AddSubmissionToApplicationHandler,
    CancelApplicationHandler,
    CreateApplicationHandler,
    GetApplicationHandler,
    ListApplicationsHandler,
    ListDraftApplicationsHandler,
    MarkApplicationPaidHandler,
    RecordConsentsHandler,
    RemoveSubmissionFromApplicationHandler,
    RequestApplicationPaymentHandler,
    SelectAdditionalServiceHandler,
    SelectEducationalOrganizationHandler,
    SubmitApplicationHandler,
)
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    BirthDate,
    DisciplineId,
    Duration,
    Gender,
    Money,
    NominationId,
    ParticipantGroupId,
    ParticipantId,
    ParticipationFormatId,
    Performance,
    PerformanceTitle,
    PersonName,
    PriceSnapshot,
    SubmissionId,
    SubmissionStatus,
)

from .fakes import (
    NOW,
    FakeApplicationRepository,
    FakeClock,
    FakeCompetitionCatalog,
    FakeCompetitionServiceCatalog,
    FakeEducationalOrganizationDirectory,
    FakeIdentityReadModel,
    FakeSubmissionRepository,
    RecordingEventPublisher,
    SequenceUuidGenerator,
    uuid7_str,
)


class Env:
    def __init__(
        self,
        *,
        catalog: FakeCompetitionCatalog | None = None,
        identity: FakeIdentityReadModel | None = None,
        services: FakeCompetitionServiceCatalog | None = None,
        directory: FakeEducationalOrganizationDirectory | None = None,
    ) -> None:
        self.applications = FakeApplicationRepository()
        self.submissions = FakeSubmissionRepository()
        self.catalog = catalog or FakeCompetitionCatalog()
        self.identity = identity or FakeIdentityReadModel()
        self.services = services or FakeCompetitionServiceCatalog()
        self.directory = directory or FakeEducationalOrganizationDirectory()
        self.clock = FakeClock()
        self.uuids = SequenceUuidGenerator()
        self.events = RecordingEventPublisher()

    def create(self) -> CreateApplicationHandler:
        return CreateApplicationHandler(
            applications=self.applications, catalog=self.catalog, identity=self.identity, clock=self.clock, uuids=self.uuids
        )

    def add_submission(self) -> AddSubmissionToApplicationHandler:
        return AddSubmissionToApplicationHandler(
            applications=self.applications, submissions=self.submissions, clock=self.clock, uuids=self.uuids, events=self.events
        )

    def remove_submission(self) -> RemoveSubmissionFromApplicationHandler:
        return RemoveSubmissionFromApplicationHandler(
            applications=self.applications, submissions=self.submissions, clock=self.clock, events=self.events
        )

    def select_service(self) -> SelectAdditionalServiceHandler:
        return SelectAdditionalServiceHandler(applications=self.applications, submissions=self.submissions, services=self.services, clock=self.clock)

    def record_consents(self) -> RecordConsentsHandler:
        return RecordConsentsHandler(applications=self.applications, clock=self.clock)

    def select_org(self) -> SelectEducationalOrganizationHandler:
        return SelectEducationalOrganizationHandler(applications=self.applications, directory=self.directory, clock=self.clock)

    def submit(self) -> SubmitApplicationHandler:
        return SubmitApplicationHandler(
            applications=self.applications,
            submissions=self.submissions,
            catalog=self.catalog,
            services=self.services,
            clock=self.clock,
            events=self.events,
        )

    def request_payment(self) -> RequestApplicationPaymentHandler:
        return RequestApplicationPaymentHandler(applications=self.applications, submissions=self.submissions, clock=self.clock)

    def mark_paid(self) -> MarkApplicationPaidHandler:
        return MarkApplicationPaidHandler(
            applications=self.applications, submissions=self.submissions, catalog=self.catalog, clock=self.clock, events=self.events
        )

    def cancel(self) -> CancelApplicationHandler:
        return CancelApplicationHandler(applications=self.applications, submissions=self.submissions, clock=self.clock, events=self.events)

    def get(self) -> GetApplicationHandler:
        return GetApplicationHandler(applications=self.applications)

    def list(self) -> ListApplicationsHandler:
        return ListApplicationsHandler(applications=self.applications)

    def drafts(self) -> ListDraftApplicationsHandler:
        return ListDraftApplicationsHandler(applications=self.applications)

    # -- test helpers driving the separate Submission workflow --------------

    def build_submittable(self, submission_id_str: str) -> None:
        """Give the submission a performance, a participant, and a frozen price."""
        submission = self.submissions.get(SubmissionId.from_string(submission_id_str))
        assert submission is not None
        performance = Performance(
            title=PerformanceTitle("Swan Lake"),
            duration=Duration.of(minutes=3),
            nomination_id=NominationId.from_uuid(SubmissionId.generate().value),
            discipline_id=DisciplineId.from_uuid(SubmissionId.generate().value),
            age_category_id=AgeCategoryId.from_uuid(SubmissionId.generate().value),
            participant_group_id=ParticipantGroupId.from_uuid(SubmissionId.generate().value),
            participation_format_id=ParticipationFormatId.from_uuid(SubmissionId.generate().value),
        )
        submission.set_performance(performance=performance, now=NOW)
        submission.add_participant(
            participant_id=ParticipantId.from_uuid(SubmissionId.generate().value),
            name=PersonName(first_name="Anna", last_name="Ivanova"),
            birth_date=BirthDate(date(2014, 5, 1)),
            gender=Gender.FEMALE,
            now=NOW,
        )
        submission.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("300.00"), calculated_at=NOW), now=NOW)
        self.submissions.save(submission)

    def approve(self, submission_id_str: str) -> None:
        """Drive a SUBMITTED submission through review to APPROVED."""
        submission = self.submissions.get(SubmissionId.from_string(submission_id_str))
        assert submission is not None
        submission.begin_review(now=NOW)
        submission.approve(now=NOW)
        self.submissions.save(submission)


def _create_app(env: Env, applicant: str | None = None) -> tuple[str, str]:
    applicant = applicant or uuid7_str()
    result = env.create().handle(CreateApplicationCommand(requested_by=applicant, competition_id=uuid7_str()))
    return result.application.id, applicant


def _add_submission(env: Env, app_id: str, applicant: str) -> str:
    result = env.add_submission().handle(AddSubmissionToApplicationCommand(requested_by=applicant, application_id=app_id))
    return result.application.submissions[-1].submission_id


class TestCreate:
    def test_creates_draft(self) -> None:
        env = Env()
        result = env.create().handle(CreateApplicationCommand(requested_by=uuid7_str(), competition_id=uuid7_str()))
        assert result.application.status == "DRAFT"
        assert len(env.applications.saved) == 1

    def test_unknown_applicant_rejected(self) -> None:
        env = Env(identity=FakeIdentityReadModel(known=False))
        with pytest.raises(ApplicantNotFoundError):
            env.create().handle(CreateApplicationCommand(requested_by=uuid7_str(), competition_id=uuid7_str()))

    def test_unknown_competition_rejected(self) -> None:
        env = Env(catalog=FakeCompetitionCatalog(known=False))
        with pytest.raises(CompetitionNotFoundError):
            env.create().handle(CreateApplicationCommand(requested_by=uuid7_str(), competition_id=uuid7_str()))

    def test_closed_competition_rejected(self) -> None:
        env = Env(catalog=FakeCompetitionCatalog(open_for_submissions=False))
        with pytest.raises(CompetitionClosedError):
            env.create().handle(CreateApplicationCommand(requested_by=uuid7_str(), competition_id=uuid7_str()))


class TestComposition:
    def test_add_submission_attaches_ref(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        result = env.add_submission().handle(AddSubmissionToApplicationCommand(requested_by=applicant, application_id=app_id))
        assert len(result.application.submissions) == 1
        assert len(env.submissions.saved) == 1

    def test_non_owner_cannot_add(self) -> None:
        env = Env()
        app_id, _ = _create_app(env)
        with pytest.raises(PermissionDeniedError):
            env.add_submission().handle(AddSubmissionToApplicationCommand(requested_by=uuid7_str(), application_id=app_id))

    def test_select_service_derives_quantity_from_billing_model(self) -> None:
        # PER_PARTICIPANT: the billed quantity is the participant count across the
        # order's applicable performances, not the client-supplied number.
        env = Env(services=FakeCompetitionServiceCatalog(service_price=Money.of("25.00")))
        app_id, applicant = _create_app(env)
        for _ in range(2):
            env.build_submittable(_add_submission(env, app_id, applicant))
        result = env.select_service().handle(
            SelectAdditionalServiceCommand(requested_by=applicant, application_id=app_id, service_id=uuid7_str(), quantity=99)
        )
        assert result.application.total_price is not None
        assert result.application.services[0].quantity == 2  # two participants, client's 99 ignored
        assert result.application.total_price.services_amount == "50.00"

    def test_service_not_available_for_order_formats_is_rejected(self) -> None:
        env = Env(services=FakeCompetitionServiceCatalog(available_format_ids=frozenset({uuid7_str()})))
        app_id, applicant = _create_app(env)
        with pytest.raises(AdditionalServiceNotAvailableError):
            env.select_service().handle(SelectAdditionalServiceCommand(requested_by=applicant, application_id=app_id, service_id=uuid7_str()))

    def test_unknown_service_rejected(self) -> None:
        env = Env(services=FakeCompetitionServiceCatalog(service_known=False))
        app_id, applicant = _create_app(env)
        with pytest.raises(AdditionalServiceNotFoundError):
            env.select_service().handle(SelectAdditionalServiceCommand(requested_by=applicant, application_id=app_id, service_id=uuid7_str()))

    def test_select_educational_organization(self) -> None:
        env = Env(directory=FakeEducationalOrganizationDirectory(name="Gymnasium 5"))
        app_id, applicant = _create_app(env)
        result = env.select_org().handle(
            SelectEducationalOrganizationCommand(requested_by=applicant, application_id=app_id, educational_organization_id=uuid7_str())
        )
        assert result.application.organization_name == "Gymnasium 5"

    def test_unknown_organization_rejected(self) -> None:
        env = Env(directory=FakeEducationalOrganizationDirectory(known=False))
        app_id, applicant = _create_app(env)
        with pytest.raises(EducationalOrganizationNotFoundError):
            env.select_org().handle(
                SelectEducationalOrganizationCommand(requested_by=applicant, application_id=app_id, educational_organization_id=uuid7_str())
            )

    def test_remove_submission_cancels_it(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        result = env.remove_submission().handle(
            RemoveSubmissionFromApplicationCommand(requested_by=applicant, application_id=app_id, submission_id=submission_id)
        )
        assert result.application.submissions == ()
        cancelled = env.submissions.get(SubmissionId.from_string(submission_id))
        assert cancelled is not None
        assert cancelled.status is SubmissionStatus.CANCELLED


class TestSubmitAndPay:
    def test_submit_requires_submissions(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        with pytest.raises(ApplicationInvariantViolationError):
            env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))

    def test_submit_enforces_required_consents(self) -> None:
        env = Env(services=FakeCompetitionServiceCatalog(required_consents=frozenset({"personal_data"})))
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)
        with pytest.raises(ApplicationInvariantViolationError):
            env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))

    def test_submit_happy_path_submits_children(self) -> None:
        env = Env(services=FakeCompetitionServiceCatalog(required_consents=frozenset({"personal_data"})))
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)
        env.record_consents().handle(
            RecordConsentsCommand(requested_by=applicant, application_id=app_id, consents=(ConsentInput(code="personal_data", version="v1"),))
        )
        result = env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))
        assert result.application.status == "SUBMITTED"
        assert result.application.submissions[0].status == "SUBMITTED"
        assert result.application.total_price is not None
        assert result.application.total_price.submissions_amount == "300.00"

    def test_submit_enforces_required_services(self) -> None:
        env = Env(services=FakeCompetitionServiceCatalog(required_services=frozenset({uuid7_str()})))
        app_id, applicant = _create_app(env)
        env.build_submittable(_add_submission(env, app_id, applicant))
        with pytest.raises(ApplicationInvariantViolationError):
            env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))

    def test_request_payment_requires_all_approved(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)
        env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))
        with pytest.raises(ApplicationInvariantViolationError):
            env.request_payment().handle(RequestApplicationPaymentCommand(requested_by=applicant, application_id=app_id))

    def test_mark_paid_rejected_after_payment_deadline(self) -> None:
        env = Env(catalog=FakeCompetitionCatalog(accepts_payment=False))
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)
        env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))
        env.approve(submission_id)
        env.request_payment().handle(RequestApplicationPaymentCommand(requested_by=applicant, application_id=app_id))
        with pytest.raises(DeadlinePassedError):
            env.mark_paid().handle(MarkApplicationPaidCommand(requested_by=applicant, application_id=app_id))

    def test_full_flow_to_paid_accepts_submissions(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)
        env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))
        env.approve(submission_id)
        pay = env.request_payment().handle(RequestApplicationPaymentCommand(requested_by=applicant, application_id=app_id))
        assert pay.application.status == "WAITING_PAYMENT"
        paid = env.mark_paid().handle(MarkApplicationPaidCommand(requested_by=applicant, application_id=app_id))
        assert paid.application.status == "PAID"
        accepted = env.submissions.get(SubmissionId.from_string(submission_id))
        assert accepted is not None
        assert accepted.status is SubmissionStatus.ACCEPTED


class TestCancel:
    def test_cancel_cancels_submissions(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        result = env.cancel().handle(CancelApplicationCommand(requested_by=applicant, application_id=app_id))
        assert result.application.status == "CANCELLED"
        cancelled = env.submissions.get(SubmissionId.from_string(submission_id))
        assert cancelled is not None
        assert cancelled.status is SubmissionStatus.CANCELLED


class TestQueries:
    def test_get_requires_owner(self) -> None:
        env = Env()
        app_id, _ = _create_app(env)
        with pytest.raises(PermissionDeniedError):
            env.get().handle(GetApplicationQuery(application_id=app_id, requested_by=uuid7_str()))

    def test_list_and_drafts(self) -> None:
        env = Env()
        applicant = uuid7_str()
        app_id, _ = _create_app(env, applicant)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)
        env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))
        _create_app(env, applicant)  # a second, still-draft application

        listed = env.list().handle(ListApplicationsQuery(applicant_id=applicant))
        assert len(listed) == 2
        drafts = env.drafts().handle(ListDraftApplicationsQuery(applicant_id=applicant))
        assert len(drafts) == 1
        assert drafts[0].status == "DRAFT"
