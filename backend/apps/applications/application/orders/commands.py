"""Command handlers (use cases) for the Application (order) aggregate.

Each handler is a thin orchestrator: it loads the order, enforces ownership,
resolves any cross-context facts through the ACL ports, executes the aggregate's
behaviour (and, where an operation spans both aggregates, the matching
:class:`Submission` behaviour), persists, and returns an
:class:`ApplicationOperationResultDto` with the collected events.

Two aggregates, two error trees: order-aggregate calls run inside
:func:`translate_application_domain_errors`; Submission-aggregate calls run inside
:func:`translate_domain_errors`.
"""

from __future__ import annotations

from datetime import datetime

from apps.applications.application.dto.order_commands import (
    AddSubmissionToApplicationCommand,
    CancelApplicationCommand,
    CompleteApplicationCommand,
    CreateApplicationCommand,
    MarkApplicationPaidCommand,
    RecordConsentsCommand,
    RemoveAdditionalServiceCommand,
    RemoveSubmissionFromApplicationCommand,
    RequestApplicationPaymentCommand,
    SelectAdditionalServiceCommand,
    SelectEducationalOrganizationCommand,
    SubmitApplicationCommand,
    SyncApplicationCommand,
)
from apps.applications.application.dto.orders import ApplicationOperationResultDto
from apps.applications.application.exceptions import (
    AdditionalServiceNotFoundError,
    ApplicantNotFoundError,
    CompetitionClosedError,
    CompetitionCombinationNotFoundError,
    CompetitionNotFoundError,
    EducationalOrganizationNotFoundError,
    SubmissionInvariantViolationError,
    translate_application_domain_errors,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    ApplicationRepository,
    Clock,
    CompetitionCatalog,
    CompetitionServiceCatalog,
    EducationalOrganizationDirectory,
    EventPublisher,
    IdentityReadModel,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.value_objects import (
    ApplicationId,
    CompetitionId,
    Consent,
    EducationalOrganizationId,
    OrganizationName,
    ServiceId,
    ServiceLine,
    SubmissionId,
    SubmissionStatus,
)

from ._support import (
    ensure_owner,
    load_application,
    parse_application_id,
    parse_user_id,
    ref_from_submission,
    refresh_submission_refs,
)

__all__ = [
    "AddSubmissionToApplicationHandler",
    "CancelApplicationHandler",
    "CompleteApplicationHandler",
    "CreateApplicationHandler",
    "MarkApplicationPaidHandler",
    "RecordConsentsHandler",
    "RemoveAdditionalServiceHandler",
    "RemoveSubmissionFromApplicationHandler",
    "RequestApplicationPaymentHandler",
    "SelectAdditionalServiceHandler",
    "SelectEducationalOrganizationHandler",
    "SubmitApplicationHandler",
    "SyncApplicationHandler",
]

#: Submission statuses that are terminal (no cancellation possible / meaningful).
_TERMINAL_SUBMISSION_STATUSES = frozenset({SubmissionStatus.CANCELLED, SubmissionStatus.COMPLETED})


class CreateApplicationHandler:
    """Use case: create a new DRAFT application (order) for a competition."""

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        catalog: CompetitionCatalog,
        identity: IdentityReadModel,
        clock: Clock,
        uuids: UuidGenerator,
    ) -> None:
        self._applications = applications
        self._catalog = catalog
        self._identity = identity
        self._clock = clock
        self._uuids = uuids

    def handle(self, command: CreateApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        applicant_id = parse_user_id(command.requested_by)
        with translate_domain_errors():
            competition_id = CompetitionId.from_string(command.competition_id)

        if not self._identity.exists(user_id=applicant_id):
            raise ApplicantNotFoundError("The applicant does not exist.")
        if not self._catalog.exists(competition_id):
            raise CompetitionNotFoundError(f"No competition {competition_id.json()}.")
        if not self._catalog.accepts_submissions(competition_id=competition_id, now=now):
            raise CompetitionClosedError("This competition is not currently accepting submissions.")

        application, events = Application.create(
            application_id=ApplicationId.from_uuid(self._uuids.new()),
            competition_id=competition_id,
            applicant_id=applicant_id,
            now=now,
        )
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(events))


class AddSubmissionToApplicationHandler:
    """Use case: create a fresh draft submission within the order and attach it."""

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: AddSubmissionToApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))

        submission, submission_events = Submission.draft(
            submission_id=SubmissionId.from_uuid(self._uuids.new()),
            competition_id=application.competition_id,
            applicant_id=application.applicant_id,
            now=now,
        )
        self._submissions.save(submission)
        self._events.publish(submission_events)

        with translate_application_domain_errors():
            order_events = application.attach_submission(ref=ref_from_submission(submission), now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class RemoveSubmissionFromApplicationHandler:
    """Use case: detach a submission from the order and cancel it (never a hard delete)."""

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._clock = clock
        self._events = events

    def handle(self, command: RemoveSubmissionFromApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        with translate_domain_errors():
            submission_id = SubmissionId.from_string(command.submission_id)

        with translate_application_domain_errors():
            order_events = application.detach_submission(submission_id=submission_id, now=now)

        submission = self._submissions.get(submission_id)
        if submission is not None and submission.status not in _TERMINAL_SUBMISSION_STATUSES:
            with translate_domain_errors():
                submission_events = submission.cancel(now=now)
            self._submissions.save(submission)
            self._events.publish(submission_events)

        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class SelectAdditionalServiceHandler:
    """Use case: select a competition additional service on the order."""

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        services: CompetitionServiceCatalog,
        clock: Clock,
    ) -> None:
        self._applications = applications
        self._services = services
        self._clock = clock

    def handle(self, command: SelectAdditionalServiceCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        with translate_application_domain_errors():
            service_id = ServiceId.from_string(command.service_id)

        quote = self._services.get_additional_service(competition_id=application.competition_id, service_id=service_id)
        if quote is None:
            raise AdditionalServiceNotFoundError(f"No additional service {service_id.json()} in this competition.")

        with translate_application_domain_errors():
            line = ServiceLine(service_id=service_id, name=quote.name, unit_price=quote.unit_price, quantity=command.quantity)
            order_events = application.add_service(service_line=line, now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class RemoveAdditionalServiceHandler:
    """Use case: remove a previously selected additional service from the order."""

    def __init__(self, *, applications: ApplicationRepository, clock: Clock) -> None:
        self._applications = applications
        self._clock = clock

    def handle(self, command: RemoveAdditionalServiceCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        with translate_application_domain_errors():
            service_id = ServiceId.from_string(command.service_id)
            order_events = application.remove_service(service_id=service_id, now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class RecordConsentsHandler:
    """Use case: record the set of accepted consents on the order."""

    def __init__(self, *, applications: ApplicationRepository, clock: Clock) -> None:
        self._applications = applications
        self._clock = clock

    def handle(self, command: RecordConsentsCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        with translate_application_domain_errors():
            consents = [Consent(code=item.code, version=item.version, accepted_at=now) for item in command.consents]
            order_events = application.record_consents(consents=consents, now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class SelectEducationalOrganizationHandler:
    """Use case: select the applicant's educational organization for the order."""

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        directory: EducationalOrganizationDirectory,
        clock: Clock,
    ) -> None:
        self._applications = applications
        self._directory = directory
        self._clock = clock

    def handle(self, command: SelectEducationalOrganizationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        with translate_application_domain_errors():
            organization_id = EducationalOrganizationId.from_string(command.educational_organization_id)

        info = self._directory.get(organization_id=organization_id)
        if info is None:
            raise EducationalOrganizationNotFoundError(f"No educational organization {organization_id.json()}.")

        with translate_application_domain_errors():
            order_events = application.select_educational_organization(
                educational_organization_id=organization_id,
                organization_name=OrganizationName(info.name),
                now=now,
            )
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class SubmitApplicationHandler:
    """Use case: submit the order - submit each attached submission, then place the order.

    Each submission is submitted through its own aggregate against the participation
    policy the Competition ACL projects for its combination; the order is then
    submitted, which freezes the total price and checks the competition's required
    consents. Refreshing the cached snapshots afterwards records each submission's new
    SUBMITTED status on the order.
    """

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        services: CompetitionServiceCatalog,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._services = services
        self._clock = clock
        self._events = events

    def handle(self, command: SubmitApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))

        for ref in application.submission_refs:
            submission = self._submissions.get(ref.submission_id)
            if submission is None or submission.status is not SubmissionStatus.DRAFT:
                continue
            self._submit_one(submission, now=now)

        refresh_submission_refs(application, self._submissions, now=now)
        required = self._services.required_consent_codes(competition_id=application.competition_id)
        with translate_application_domain_errors():
            order_events = application.submit(required_consent_codes=required, now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))

    def _submit_one(self, submission: Submission, *, now: datetime) -> None:
        performance = submission.performance
        if performance is None:
            raise SubmissionInvariantViolationError(
                "A submission has no performance and cannot be submitted.",
                domain_code="PerformanceRequiredError",
            )
        policy = self._catalog.participation_policy(
            competition_id=submission.competition_id,
            nomination_id=performance.nomination_id,
            discipline_id=performance.discipline_id,
            age_category_id=performance.age_category_id,
            participant_group_id=performance.participant_group_id,
            participation_format_id=performance.participation_format_id,
        )
        if policy is None:
            raise CompetitionCombinationNotFoundError("The competition has no configuration for this combination.")
        with translate_domain_errors():
            submission_events = submission.submit(policy=policy, now=now)
        self._submissions.save(submission)
        self._events.publish(submission_events)


class RequestApplicationPaymentHandler:
    """Use case: move the order to awaiting payment (requires all submissions approved)."""

    def __init__(self, *, applications: ApplicationRepository, submissions: SubmissionRepository, clock: Clock) -> None:
        self._applications = applications
        self._submissions = submissions
        self._clock = clock

    def handle(self, command: RequestApplicationPaymentCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        refresh_submission_refs(application, self._submissions, now=now)
        with translate_application_domain_errors():
            order_events = application.request_payment(now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class MarkApplicationPaidHandler:
    """Use case: record the order's payment and accept its approved submissions.

    Payment settles once for the whole order. On payment the order moves to PAID and
    each approved submission is advanced through its own payment tail
    (APPROVED -> WAITING_PAYMENT -> PAID -> ACCEPTED), so the performances are
    committed to the running order.
    """

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._clock = clock
        self._events = events

    def handle(self, command: MarkApplicationPaidCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        with translate_application_domain_errors():
            order_events = application.mark_paid(now=now)

        for ref in application.submission_refs:
            submission = self._submissions.get(ref.submission_id)
            if submission is None or submission.status is not SubmissionStatus.APPROVED:
                continue
            with translate_domain_errors():
                accept_events = [
                    *submission.await_payment(now=now),
                    *submission.mark_paid(now=now),
                    *submission.accept(now=now),
                ]
            self._submissions.save(submission)
            self._events.publish(accept_events)

        refresh_submission_refs(application, self._submissions, now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class CompleteApplicationHandler:
    """Use case: mark the order as fully settled (PAID -> COMPLETED)."""

    def __init__(self, *, applications: ApplicationRepository, clock: Clock) -> None:
        self._applications = applications
        self._clock = clock

    def handle(self, command: CompleteApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        with translate_application_domain_errors():
            order_events = application.complete(now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class CancelApplicationHandler:
    """Use case: cancel the order and cancel its non-terminal submissions."""

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._clock = clock
        self._events = events

    def handle(self, command: CancelApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        with translate_application_domain_errors():
            order_events = application.cancel(now=now)

        for ref in application.submission_refs:
            submission = self._submissions.get(ref.submission_id)
            if submission is None or submission.status in _TERMINAL_SUBMISSION_STATUSES:
                continue
            with translate_domain_errors():
                submission_events = submission.cancel(now=now)
            self._submissions.save(submission)
            self._events.publish(submission_events)

        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class SyncApplicationHandler:
    """Use case: refresh the order's cached submission snapshots from live submissions."""

    def __init__(self, *, applications: ApplicationRepository, submissions: SubmissionRepository, clock: Clock) -> None:
        self._applications = applications
        self._submissions = submissions
        self._clock = clock

    def handle(self, command: SyncApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        refresh_submission_refs(application, self._submissions, now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, ())
