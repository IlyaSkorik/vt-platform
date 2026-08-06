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
    RemoveApplicationReceiptCommand,
    RemoveSubmissionFromApplicationCommand,
    RequestApplicationPaymentCommand,
    SelectAdditionalServiceCommand,
    SelectEducationalOrganizationCommand,
    SubmitApplicationCommand,
    UploadApplicationReceiptCommand,
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
    ApplicationReferenceNotFoundError,
    ApplicationStateConflictError,
    CompetitionClosedError,
    CompetitionNotFoundError,
    DeadlinePassedError,
    EducationalOrganizationNotFoundError,
    FileTooLargeError,
    PaymentReceiptRequiredError,
    PermissionDeniedError,
    UnsupportedFileTypeError,
)
from apps.applications.application.interfaces import ReceiptRequirement
from apps.applications.application.orders import (
    AddSubmissionToApplicationHandler,
    CancelApplicationHandler,
    CreateApplicationHandler,
    GetApplicationHandler,
    ListApplicationsHandler,
    ListDraftApplicationsHandler,
    MarkApplicationPaidHandler,
    RecordConsentsHandler,
    RemoveApplicationReceiptHandler,
    RemoveSubmissionFromApplicationHandler,
    RequestApplicationPaymentHandler,
    SelectAdditionalServiceHandler,
    SelectEducationalOrganizationHandler,
    SubmitApplicationHandler,
    UploadApplicationReceiptHandler,
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
    RegistryParticipantId,
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
    FakeFileStorage,
    FakeIdentityReadModel,
    FakeParticipantGuardianRegistry,
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
        guardians: FakeParticipantGuardianRegistry | None = None,
    ) -> None:
        self.guardians = guardians or FakeParticipantGuardianRegistry()
        self.applications = FakeApplicationRepository()
        self.submissions = FakeSubmissionRepository()
        self.catalog = catalog or FakeCompetitionCatalog()
        self.identity = identity or FakeIdentityReadModel()
        self.services = services or FakeCompetitionServiceCatalog()
        self.directory = directory or FakeEducationalOrganizationDirectory()
        self.clock = FakeClock()
        self.uuids = SequenceUuidGenerator()
        self.events = RecordingEventPublisher()
        self.storage = FakeFileStorage()

    def create(self) -> CreateApplicationHandler:
        return CreateApplicationHandler(
            applications=self.applications, catalog=self.catalog, identity=self.identity, clock=self.clock, uuids=self.uuids
        )

    def add_submission(self) -> AddSubmissionToApplicationHandler:
        return AddSubmissionToApplicationHandler(
            applications=self.applications,
            submissions=self.submissions,
            catalog=self.catalog,
            clock=self.clock,
            uuids=self.uuids,
            events=self.events,
        )

    def remove_submission(self) -> RemoveSubmissionFromApplicationHandler:
        return RemoveSubmissionFromApplicationHandler(
            applications=self.applications,
            submissions=self.submissions,
            catalog=self.catalog,
            clock=self.clock,
            events=self.events,
        )

    def select_service(self) -> SelectAdditionalServiceHandler:
        return SelectAdditionalServiceHandler(
            applications=self.applications,
            submissions=self.submissions,
            catalog=self.catalog,
            services=self.services,
            clock=self.clock,
        )

    def record_consents(self) -> RecordConsentsHandler:
        return RecordConsentsHandler(applications=self.applications, catalog=self.catalog, clock=self.clock)

    def select_org(self) -> SelectEducationalOrganizationHandler:
        return SelectEducationalOrganizationHandler(applications=self.applications, catalog=self.catalog, directory=self.directory, clock=self.clock)

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
        return RequestApplicationPaymentHandler(applications=self.applications, submissions=self.submissions, catalog=self.catalog, clock=self.clock)

    def mark_paid(self) -> MarkApplicationPaidHandler:
        return MarkApplicationPaidHandler(
            applications=self.applications, submissions=self.submissions, catalog=self.catalog, clock=self.clock, events=self.events
        )

    def cancel(self) -> CancelApplicationHandler:
        return CancelApplicationHandler(applications=self.applications, submissions=self.submissions, clock=self.clock, events=self.events)

    def upload_receipt(self) -> UploadApplicationReceiptHandler:
        return UploadApplicationReceiptHandler(applications=self.applications, storage=self.storage, clock=self.clock, events=self.events)

    def remove_receipt(self) -> RemoveApplicationReceiptHandler:
        return RemoveApplicationReceiptHandler(applications=self.applications, clock=self.clock, events=self.events)

    def get(self) -> GetApplicationHandler:
        return GetApplicationHandler(applications=self.applications, submissions=self.submissions, catalog=self.catalog, clock=self.clock)

    def list(self) -> ListApplicationsHandler:
        return ListApplicationsHandler(applications=self.applications, submissions=self.submissions, catalog=self.catalog, clock=self.clock)

    def drafts(self) -> ListDraftApplicationsHandler:
        return ListDraftApplicationsHandler(applications=self.applications, submissions=self.submissions, catalog=self.catalog, clock=self.clock)

    # -- test helpers driving the separate Submission workflow --------------

    def build_submittable(self, submission_id_str: str, *, from_registry: bool = False) -> None:
        """Give the submission a performance, a participant, and a frozen price.

        ``from_registry`` links the participant back to a Participant Registry record,
        which is what the guardian requirement is checked against — a manually typed
        participant has no registry row and so can never carry a guardian link.
        """
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
            registry_participant_id=(RegistryParticipantId.from_uuid(SubmissionId.generate().value) if from_registry else None),
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

    def test_draft_read_reflects_price_calculated_after_attach(self) -> None:
        # In the wizard a performance is attached before it is priced, so its ref
        # caches a zero price. Reading the DRAFT order must refresh the ref from the
        # now-priced submission, so the previewed total includes the org fee - not
        # only the services.
        env = Env()
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)  # prices the submission at 300.00 after attach
        view = env.get().handle(GetApplicationQuery(application_id=app_id, requested_by=applicant))
        assert view.total_price is not None
        assert view.total_price.submissions_amount == "300.00"
        assert view.total_price.total_amount == "300.00"

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

    def test_submit_demands_receipt_when_late_upload_is_forbidden(self) -> None:
        env = Env(services=FakeCompetitionServiceCatalog(receipt_requirement=ReceiptRequirement(required=True, due_at_submit=True)))
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)
        with pytest.raises(PaymentReceiptRequiredError):
            env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))

    def test_submit_allows_missing_receipt_when_it_may_arrive_later(self) -> None:
        env = Env(services=FakeCompetitionServiceCatalog(receipt_requirement=ReceiptRequirement(required=True, due_at_submit=False)))
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id)
        result = env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))
        assert result.application.status == "SUBMITTED"

    def test_submit_does_not_ask_about_guardian_links(self) -> None:
        """A missing guardian link no longer blocks a submission.

        The per-festival "every participant must have a verified guardian in the registry"
        setting is gone, and with it the gate. What remains is the guardian's *consent*,
        which is required unconditionally when the child's record is created — a stronger
        guarantee, and one an organizer cannot switch off.
        """
        env = Env(guardians=FakeParticipantGuardianRegistry(all_covered=False))
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id, from_registry=True)

        result = env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))

        assert result.application.status == "SUBMITTED"

    def test_submit_accepts_a_manually_typed_participant(self) -> None:
        # No registry record at all used to be an automatic refusal under that setting.
        env = Env(guardians=FakeParticipantGuardianRegistry(all_covered=False))
        app_id, applicant = _create_app(env)
        submission_id = _add_submission(env, app_id, applicant)
        env.build_submittable(submission_id, from_registry=False)

        result = env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))

        assert result.application.status == "SUBMITTED"
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


def _reach_submitted(env: Env) -> tuple[str, str, str]:
    """Create an application with one priced, submitted submission (order SUBMITTED)."""
    app_id, applicant = _create_app(env)
    submission_id = _add_submission(env, app_id, applicant)
    env.build_submittable(submission_id)
    env.submit().handle(SubmitApplicationCommand(requested_by=applicant, application_id=app_id))
    return app_id, applicant, submission_id


def _receipt_command(
    app_id: str,
    applicant: str,
    *,
    filename: str = "receipt.pdf",
    content: bytes = b"%PDF-1.4 paid",
) -> UploadApplicationReceiptCommand:
    return UploadApplicationReceiptCommand(
        requested_by=applicant,
        application_id=app_id,
        filename=filename,
        content_type="application/pdf",
        content=content,
    )


class TestPaymentReceipt:
    def test_upload_stores_and_attaches_receipt_after_submission(self) -> None:
        env = Env()
        app_id, applicant, _ = _reach_submitted(env)
        result = env.upload_receipt().handle(_receipt_command(app_id, applicant))
        assert len(result.application.payment_receipts) == 1
        assert len(env.storage.saved) == 1

    def test_upload_allowed_while_awaiting_payment(self) -> None:
        env = Env()
        app_id, applicant, submission_id = _reach_submitted(env)
        env.approve(submission_id)
        env.request_payment().handle(RequestApplicationPaymentCommand(requested_by=applicant, application_id=app_id))
        result = env.upload_receipt().handle(_receipt_command(app_id, applicant))
        assert len(result.application.payment_receipts) == 1

    def test_upload_allowed_while_draft(self) -> None:
        # Upfront-payment festivals: the receipt may be attached while still a draft.
        env = Env()
        app_id, applicant = _create_app(env)
        result = env.upload_receipt().handle(_receipt_command(app_id, applicant))
        assert len(result.application.payment_receipts) == 1
        assert len(env.storage.saved) == 1

    def test_upload_rejected_once_settled(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        env.cancel().handle(CancelApplicationCommand(requested_by=applicant, application_id=app_id))
        with pytest.raises(ApplicationStateConflictError):
            env.upload_receipt().handle(_receipt_command(app_id, applicant))
        assert env.storage.saved == {}

    def test_upload_rejects_unsupported_type(self) -> None:
        env = Env()
        app_id, applicant, _ = _reach_submitted(env)
        with pytest.raises(UnsupportedFileTypeError):
            env.upload_receipt().handle(_receipt_command(app_id, applicant, filename="virus.exe"))
        assert env.storage.saved == {}

    def test_upload_rejects_oversized_file(self) -> None:
        env = Env()
        app_id, applicant, _ = _reach_submitted(env)
        with pytest.raises(FileTooLargeError):
            env.upload_receipt().handle(_receipt_command(app_id, applicant, content=b"x" * (15 * 1024 * 1024 + 1)))
        assert env.storage.saved == {}

    def test_upload_requires_owner(self) -> None:
        env = Env()
        app_id, _, _ = _reach_submitted(env)
        with pytest.raises(PermissionDeniedError):
            env.upload_receipt().handle(_receipt_command(app_id, uuid7_str()))

    def test_a_second_upload_adds_a_receipt_instead_of_replacing_the_first(self) -> None:
        # The whole point: a fee paid in two transfers has two slips, and the
        # organizer needs both to see the total was covered.
        env = Env()
        app_id, applicant = _create_app(env)
        env.upload_receipt().handle(_receipt_command(app_id, applicant, filename="part-one.pdf"))
        result = env.upload_receipt().handle(_receipt_command(app_id, applicant, filename="part-two.pdf"))

        assert len(result.application.payment_receipts) == 2
        assert len(env.storage.saved) == 2
        assert len({receipt.id for receipt in result.application.payment_receipts}) == 2

    def test_remove_takes_back_only_the_receipt_named(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        env.upload_receipt().handle(_receipt_command(app_id, applicant, filename="part-one.pdf"))
        uploaded = env.upload_receipt().handle(_receipt_command(app_id, applicant, filename="wrong-file.pdf"))
        kept, wrong = uploaded.application.payment_receipts

        result = env.remove_receipt().handle(RemoveApplicationReceiptCommand(requested_by=applicant, application_id=app_id, receipt_id=wrong.id))

        assert [receipt.id for receipt in result.application.payment_receipts] == [kept.id]

    def test_remove_rejects_a_receipt_not_on_the_order(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        env.upload_receipt().handle(_receipt_command(app_id, applicant))
        with pytest.raises(ApplicationReferenceNotFoundError):
            env.remove_receipt().handle(RemoveApplicationReceiptCommand(requested_by=applicant, application_id=app_id, receipt_id=uuid7_str()))

    def test_remove_requires_owner(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        uploaded = env.upload_receipt().handle(_receipt_command(app_id, applicant))
        receipt_id = uploaded.application.payment_receipts[0].id
        with pytest.raises(PermissionDeniedError):
            env.remove_receipt().handle(RemoveApplicationReceiptCommand(requested_by=uuid7_str(), application_id=app_id, receipt_id=receipt_id))

    def test_remove_rejected_once_settled(self) -> None:
        env = Env()
        app_id, applicant = _create_app(env)
        uploaded = env.upload_receipt().handle(_receipt_command(app_id, applicant))
        receipt_id = uploaded.application.payment_receipts[0].id
        env.cancel().handle(CancelApplicationCommand(requested_by=applicant, application_id=app_id))
        with pytest.raises(ApplicationStateConflictError):
            env.remove_receipt().handle(RemoveApplicationReceiptCommand(requested_by=applicant, application_id=app_id, receipt_id=receipt_id))
