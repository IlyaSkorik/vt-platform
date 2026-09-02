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

from datetime import datetime, timedelta
from pathlib import PurePosixPath
from typing import Final

from apps.applications.application.dto.order_commands import (
    AddSubmissionToApplicationCommand,
    CancelApplicationCommand,
    CompleteApplicationCommand,
    CreateApplicationCommand,
    MarkApplicationPaidCommand,
    RecordConsentsCommand,
    RemoveAdditionalServiceCommand,
    RemoveApplicationReceiptCommand,
    RemoveSubmissionFromApplicationCommand,
    RequestApplicationPaymentCommand,
    SelectAdditionalServiceCommand,
    SelectEducationalOrganizationCommand,
    SubmitApplicationCommand,
    SyncApplicationCommand,
    UploadApplicationReceiptCommand,
)
from apps.applications.application.dto.orders import ApplicationOperationResultDto
from apps.applications.application.exceptions import (
    AdditionalServiceNotAvailableError,
    AdditionalServiceNotFoundError,
    ApplicantNotFoundError,
    ApplicationStateConflictError,
    CompetitionClosedError,
    CompetitionCombinationNotFoundError,
    CompetitionNotFoundError,
    DeadlinePassedError,
    EducationalOrganizationNotFoundError,
    FileTooLargeError,
    MultiplePerformancesNotAllowedError,
    PaymentReceiptRequiredError,
    SubmissionInvariantViolationError,
    UnsupportedFileTypeError,
    translate_application_domain_errors,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    ApplicantNotifier,
    ApplicationRepository,
    Clock,
    CompetitionCatalog,
    CompetitionOrganizerDirectory,
    CompetitionServiceCatalog,
    EducationalOrganizationDirectory,
    EventPublisher,
    FileStorage,
    IdentityReadModel,
    OrganizerNotifier,
    PendingRevisions,
    RevisionJournal,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.value_objects import (
    ApplicationId,
    ApplicationStatus,
    CompetitionId,
    Consent,
    EducationalOrganizationId,
    FileReference,
    OrganizationName,
    PaymentReceiptId,
    PriceCalculationType,
    ServiceId,
    ServiceLine,
    SubmissionId,
    SubmissionStatus,
)

from ._support import (
    ensure_owner,
    load_application,
    load_order_submissions,
    order_participation_format_ids,
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
    "NotifyOrganizerOfRevisionsHandler",
    "RecordConsentsHandler",
    "RemoveAdditionalServiceHandler",
    "RemoveApplicationReceiptHandler",
    "RemoveSubmissionFromApplicationHandler",
    "RequestApplicationPaymentHandler",
    "SelectAdditionalServiceHandler",
    "SelectEducationalOrganizationHandler",
    "SubmitApplicationHandler",
    "SyncApplicationHandler",
    "UploadApplicationReceiptHandler",
]

#: Submission statuses that are terminal (no cancellation possible / meaningful).
_TERMINAL_SUBMISSION_STATUSES = frozenset({SubmissionStatus.CANCELLED, SubmissionStatus.COMPLETED})

#: Submission statuses from which a submission can no longer be cancelled: the
#: terminal ones plus those already committed to the competition. Cancelling an
#: order skips these children instead of attempting an illegal transition.
_UNCANCELLABLE_SUBMISSION_STATUSES = frozenset(
    {
        SubmissionStatus.ACCEPTED,
        SubmissionStatus.SCHEDULED,
        SubmissionStatus.COMPLETED,
        SubmissionStatus.CANCELLED,
    }
)

#: How long an applicant has to attach a payment receipt after submitting before the
#: order is auto-cancelled.
_PAYMENT_RECEIPT_WINDOW = timedelta(hours=48)

#: Order statuses from which an unpaid order may still be auto-cancelled.
_AUTO_CANCELLABLE_STATUSES = frozenset({ApplicationStatus.SUBMITTED, ApplicationStatus.WAITING_PAYMENT})

#: How long an order must go unedited before its journalled edits are reported to the
#: organizer. Filling in a teacher, then a participant, then a phonogram is one act of
#: editing; without a pause to wait for, it would be three letters.
_REVISION_QUIET_PERIOD = timedelta(minutes=5)

#: Fixed constraints for the order-level payment receipt (a PDF or an image scan).
#: Unlike per-performance uploads there is no competition format to key off, so the
#: platform applies one sensible limit for proof-of-payment documents.
_RECEIPT_MAX_BYTES: Final = 15 * 1024 * 1024
_RECEIPT_ALLOWED_EXTENSIONS: Final = frozenset({"pdf", "jpg", "jpeg", "png", "webp", "heic"})


def _applicable_submissions(order_submissions: list[Submission], available_format_ids: frozenset[str]) -> list[Submission]:
    """The order's performances a service applies to (all with a format if unscoped)."""
    with_performance = [s for s in order_submissions if s.performance is not None]
    if not available_format_ids:
        return with_performance
    return [s for s in with_performance if s.performance is not None and s.performance.participation_format_id.json() in available_format_ids]


def _billed_quantity(billing_model: PriceCalculationType, applicable: list[Submission]) -> int:
    """Derive the service's billed quantity from its billing model (never trusted from the client)."""
    if billing_model is PriceCalculationType.PER_PERFORMANCE:
        return max(1, len(applicable))
    return max(1, sum(submission.participant_count for submission in applicable))


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
        catalog: CompetitionCatalog,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: AddSubmissionToApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        if not self._catalog.accepts_submissions(competition_id=application.competition_id, now=now):
            raise CompetitionClosedError("Регистрация закрыта: редактирование заявки недоступно.")
        # Checked here rather than on the aggregate: how many performances a festival
        # wants is the Competition's rule, and the order has no way to know it. The
        # count is the order's *current* refs, so removing a performance frees the
        # slot again — the wizard's own back-out has to keep working.
        if application.submission_count and not self._catalog.allows_multiple_performances(competition_id=application.competition_id):
            raise MultiplePerformancesNotAllowedError("Фестиваль принимает по одному выступлению в заявке.")

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
        catalog: CompetitionCatalog,
        clock: Clock,
        events: EventPublisher,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock
        self._events = events

    def handle(self, command: RemoveSubmissionFromApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        if not self._catalog.accepts_submissions(competition_id=application.competition_id, now=now):
            raise CompetitionClosedError("Регистрация закрыта: редактирование заявки недоступно.")
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
    """Use case: select a competition additional service on the order.

    Enforces the organizer's configuration: the service must be available for at
    least one of the order's chosen participation formats, and the billed quantity
    is derived from its ``billing_model`` (per participant across the applicable
    performances, or per performance) rather than trusted from the client.
    """

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        services: CompetitionServiceCatalog,
        clock: Clock,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._services = services
        self._clock = clock

    def handle(self, command: SelectAdditionalServiceCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        if not self._catalog.accepts_submissions(competition_id=application.competition_id, now=now):
            raise CompetitionClosedError("Регистрация закрыта: редактирование заявки недоступно.")
        with translate_application_domain_errors():
            service_id = ServiceId.from_string(command.service_id)

        quote = self._services.get_additional_service(competition_id=application.competition_id, service_id=service_id)
        if quote is None:
            raise AdditionalServiceNotFoundError(f"No additional service {service_id.json()} in this competition.")

        order_submissions = load_order_submissions(application, self._submissions)
        applicable = _applicable_submissions(order_submissions, quote.available_format_ids)
        if quote.available_format_ids and not applicable:
            raise AdditionalServiceNotAvailableError(
                f"Service {service_id.json()} is not available for any participation format in this application."
            )
        quantity = _billed_quantity(quote.billing_model, applicable or order_submissions)

        with translate_application_domain_errors():
            line = ServiceLine(
                service_id=service_id,
                name=quote.name,
                unit_price=quote.unit_price,
                quantity=quantity,
                billing_model=quote.billing_model,
            )
            order_events = application.add_service(service_line=line, now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class RemoveAdditionalServiceHandler:
    """Use case: remove a previously selected additional service from the order."""

    def __init__(self, *, applications: ApplicationRepository, catalog: CompetitionCatalog, clock: Clock) -> None:
        self._applications = applications
        self._catalog = catalog
        self._clock = clock

    def handle(self, command: RemoveAdditionalServiceCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        if not self._catalog.accepts_submissions(competition_id=application.competition_id, now=now):
            raise CompetitionClosedError("Регистрация закрыта: редактирование заявки недоступно.")
        with translate_application_domain_errors():
            service_id = ServiceId.from_string(command.service_id)
            order_events = application.remove_service(service_id=service_id, now=now)
        self._applications.save(application)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class RecordConsentsHandler:
    """Use case: record the set of accepted consents on the order."""

    def __init__(self, *, applications: ApplicationRepository, catalog: CompetitionCatalog, clock: Clock) -> None:
        self._applications = applications
        self._catalog = catalog
        self._clock = clock

    def handle(self, command: RecordConsentsCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        if not self._catalog.accepts_submissions(competition_id=application.competition_id, now=now):
            raise CompetitionClosedError("Регистрация закрыта: редактирование заявки недоступно.")
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
        catalog: CompetitionCatalog,
        directory: EducationalOrganizationDirectory,
        clock: Clock,
    ) -> None:
        self._applications = applications
        self._catalog = catalog
        self._directory = directory
        self._clock = clock

    def handle(self, command: SelectEducationalOrganizationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        if not self._catalog.accepts_submissions(competition_id=application.competition_id, now=now):
            raise CompetitionClosedError("Регистрация закрыта: редактирование заявки недоступно.")
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
        identity: IdentityReadModel | None = None,
        notifier: ApplicantNotifier | None = None,
        payment_window: timedelta = _PAYMENT_RECEIPT_WINDOW,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._services = services
        self._clock = clock
        self._events = events
        self._identity = identity
        self._notifier = notifier
        self._payment_window = payment_window

    def handle(self, command: SubmitApplicationCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))

        for ref in application.submission_refs:
            submission = self._submissions.get(ref.submission_id)
            if submission is None or submission.status is not SubmissionStatus.DRAFT:
                continue
            self._submit_one(submission, now=now)

        refresh_submission_refs(
            application,
            self._submissions,
            now=now,
            additional_performance_discount_percent=self._catalog.additional_performance_discount_percent(competition_id=application.competition_id),
        )
        format_ids = order_participation_format_ids(load_order_submissions(application, self._submissions))
        required_consents = self._services.required_consent_codes(competition_id=application.competition_id)
        required_services = self._services.required_service_ids(competition_id=application.competition_id, participation_format_ids=format_ids)
        receipt = self._services.receipt_requirement(competition_id=application.competition_id, participation_format_ids=format_ids)
        if receipt.required and receipt.due_at_submit and not application.has_payment_receipt:
            raise PaymentReceiptRequiredError("This competition requires the payment receipt to be attached before the application is submitted.")
        with translate_application_domain_errors():
            order_events = application.submit(required_consent_codes=required_consents, required_service_ids=required_services, now=now)
        self._applications.save(application)
        self._notify_submitted(application, now=now)
        return ApplicationOperationResultDto.of(application, tuple(order_events))

    def _notify_submitted(self, application: Application, *, now: datetime) -> None:
        """Tell the applicant the order is submitted.

        With a receipt already attached it is a plain confirmation; otherwise it asks
        for payment by the deadline. The actual auto-cancellation is handled by the
        periodic sweep (Celery Beat), not scheduled here — see ``tasks.py``.
        """
        if self._identity is None or self._notifier is None:
            return
        applicant = self._identity.get_applicant(user_id=application.applicant_id)
        if applicant is None:
            return
        if application.has_payment_receipt:
            self._notifier.notify_application_submitted(
                user_id=applicant.user_id,
                email=applicant.email,
                applicant_name=applicant.display_name,
                application_id=application.id.json(),
            )
            return
        deadline = now + self._payment_window
        self._notifier.notify_application_awaiting_payment(
            user_id=applicant.user_id,
            email=applicant.email,
            applicant_name=applicant.display_name,
            application_id=application.id.json(),
            deadline=deadline,
        )

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

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        clock: Clock,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock

    def handle(self, command: RequestApplicationPaymentCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        refresh_submission_refs(
            application,
            self._submissions,
            now=now,
            additional_performance_discount_percent=self._catalog.additional_performance_discount_percent(competition_id=application.competition_id),
        )
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
        catalog: CompetitionCatalog,
        clock: Clock,
        events: EventPublisher,
        services: CompetitionServiceCatalog | None = None,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._catalog = catalog
        self._clock = clock
        self._events = events
        self._services = services

    def handle(self, command: MarkApplicationPaidCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))
        if not self._catalog.accepts_payment(competition_id=application.competition_id, now=now):
            raise DeadlinePassedError("The payment deadline for this competition has passed.")
        self._ensure_receipt_present(application)
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

    def _ensure_receipt_present(self, application: Application) -> None:
        """Refuse to record payment while a receipt the competition demands is missing.

        This is the ``allow_upload_later`` half of the organizer's receipt setting:
        the proof may arrive after the order is placed, but not after it is called
        paid. Skipped when no service catalog is wired (the receipt rules live
        there), so callers that never configured one behave as before.
        """
        if self._services is None or application.has_payment_receipt:
            return
        format_ids = order_participation_format_ids(load_order_submissions(application, self._submissions))
        receipt = self._services.receipt_requirement(
            competition_id=application.competition_id,
            participation_format_ids=format_ids,
        )
        if receipt.required:
            raise PaymentReceiptRequiredError("This competition requires a payment receipt before the application can be marked paid.")


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


class AutoCancelUnpaidApplicationHandler:
    """Use case: auto-cancel a submitted order whose payment receipt never arrived.

    Invoked by the deferred payment-deadline job (not by the applicant), so there is
    no ownership check. It is a safe no-op if the order has since had a receipt
    attached, been paid, or already left a cancellable state — the timer firing late
    or twice never cancels a settled order.
    """

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        submissions: SubmissionRepository,
        clock: Clock,
        events: EventPublisher,
        identity: IdentityReadModel | None = None,
        notifier: ApplicantNotifier | None = None,
    ) -> None:
        self._applications = applications
        self._submissions = submissions
        self._clock = clock
        self._events = events
        self._identity = identity
        self._notifier = notifier

    def handle(self, application_id: str) -> None:
        now = self._clock.utcnow()
        application = self._applications.get(parse_application_id(application_id))
        if application is None:
            return
        # A receipt was attached (payment proof provided) → keep the order.
        if application.has_payment_receipt:
            return
        # Already paid / completed / cancelled → nothing to do.
        if application.status not in _AUTO_CANCELLABLE_STATUSES:
            return

        with translate_application_domain_errors():
            order_events = application.cancel(now=now)
        for ref in application.submission_refs:
            submission = self._submissions.get(ref.submission_id)
            # A submission already committed to the competition (ACCEPTED/SCHEDULED)
            # or terminal cannot be cancelled — leave it in place.
            if submission is None or submission.status in _UNCANCELLABLE_SUBMISSION_STATUSES:
                continue
            with translate_domain_errors():
                submission_events = submission.cancel(now=now)
            self._submissions.save(submission)
            self._events.publish(submission_events)
        self._applications.save(application)
        self._events.publish(order_events)

        if self._identity is None or self._notifier is None:
            return
        applicant = self._identity.get_applicant(user_id=application.applicant_id)
        if applicant is not None:
            self._notifier.notify_application_auto_cancelled(
                user_id=applicant.user_id,
                email=applicant.email,
                applicant_name=applicant.display_name,
                application_id=application.id.json(),
            )


class NotifyOrganizerOfRevisionsHandler:
    """Use case: tell each organizer, once, that a placed order has been edited.

    Invoked by the periodic sweep rather than by a request: the applicant's edits are
    journalled as they are made, and this folds every edit to one order into one
    letter. The quiet period is what makes that fold meaningful - an order still being
    edited is skipped entirely and picked up by a later run, so an editing session
    produces one notice rather than one per pause.

    Idempotent by construction: the journal rows carried into a letter are stamped as
    reported, bounded by the digest's own last instant, so an edit made *while* the
    letter was going out is carried into the next one instead of being lost or sent
    twice.
    """

    def __init__(
        self,
        *,
        journal: RevisionJournal,
        organizers: CompetitionOrganizerDirectory,
        identity: IdentityReadModel,
        notifier: OrganizerNotifier,
        clock: Clock,
        quiet_period: timedelta = _REVISION_QUIET_PERIOD,
    ) -> None:
        self._journal = journal
        self._organizers = organizers
        self._identity = identity
        self._notifier = notifier
        self._clock = clock
        self._quiet_period = quiet_period

    def handle(self) -> int:
        """Send the due digests; returns how many orders were reported on."""
        now = self._clock.utcnow()
        sent = 0
        for digest in self._journal.pending(quiet_since=now - self._quiet_period):
            if self._notify(digest):
                sent += 1
            # Stamped either way. A digest nobody can be told about (a deleted
            # competition, an organization with no mailbox on file) would otherwise be
            # retried every sweep forever, and the retry cannot succeed.
            self._journal.mark_notified(application_id=digest.application_id, up_to=digest.last_at, now=now)
        return sent

    def _notify(self, digest: PendingRevisions) -> bool:
        with translate_domain_errors():
            competition_id = CompetitionId.from_string(digest.competition_id)
        organizer = self._organizers.get_organizer(competition_id=competition_id)
        if organizer is None or not organizer.emails:
            return False
        applicant = self._identity.get_applicant(user_id=parse_user_id(digest.applicant_id))
        self._notifier.notify_application_revised(
            emails=organizer.emails,
            competition_title=organizer.competition_title,
            applicant_name=applicant.display_name if applicant is not None else "—",
            application_id=digest.application_id,
            changes=digest.changes,
            revised_at=digest.last_at,
        )
        return True


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


class UploadApplicationReceiptHandler:
    """Use case: validate, store and attach one order-level payment receipt.

    A receipt proves payment for the whole order, so it lives on the Application
    (not a submission). The file is validated against the fixed receipt constraints,
    stored, and added to the order's receipts; the domain enforces that receipts may
    only be attached before the order settles, and caps how many one order holds.
    """

    def __init__(self, *, applications: ApplicationRepository, storage: FileStorage, clock: Clock, events: EventPublisher) -> None:
        self._applications = applications
        self._storage = storage
        self._clock = clock
        self._events = events

    def handle(self, command: UploadApplicationReceiptCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))

        if len(command.content) > _RECEIPT_MAX_BYTES:
            raise FileTooLargeError(f"The receipt is {len(command.content)} bytes; the maximum is {_RECEIPT_MAX_BYTES} bytes.")
        extension = PurePosixPath(command.filename).suffix.lstrip(".").lower()
        if extension not in _RECEIPT_ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(f"Files of type {extension or '(none)'!r} are not allowed for a payment receipt.")
        # Reject a wrong-state upload before storing so no orphan file is written; the
        # aggregate re-checks the same invariant when the receipt is actually attached.
        if not application.accepts_payment_receipt():
            raise ApplicationStateConflictError(
                f"A payment receipt cannot be attached once the application is settled ({application.status.value}).",
                domain_code="PaymentReceiptNotAllowedError",
            )

        reference = self._storage.save(content=command.content, filename=command.filename, content_type=command.content_type)
        with translate_application_domain_errors():
            file_reference = FileReference(reference)
            order_events = application.upload_payment_receipt(file=file_reference, now=now)
        self._applications.save(application)
        self._events.publish(order_events)
        return ApplicationOperationResultDto.of(application, tuple(order_events))


class RemoveApplicationReceiptHandler:
    """Use case: detach one of the order's payment receipts.

    The counterpart of uploading: since a second upload now *adds* a receipt rather
    than replacing the first, taking back a wrong file is its own operation. The
    stored file is left in place — the storage is append-only and an orphaned blob
    is cheaper than deleting one an audit may still want.
    """

    def __init__(self, *, applications: ApplicationRepository, clock: Clock, events: EventPublisher) -> None:
        self._applications = applications
        self._clock = clock
        self._events = events

    def handle(self, command: RemoveApplicationReceiptCommand) -> ApplicationOperationResultDto:
        now = self._clock.utcnow()
        application = load_application(self._applications, parse_application_id(command.application_id))
        ensure_owner(application, parse_user_id(command.requested_by))

        with translate_application_domain_errors():
            receipt_id = PaymentReceiptId.from_string(command.receipt_id)
            order_events = application.remove_payment_receipt(receipt_id=receipt_id, now=now)
        self._applications.save(application)
        self._events.publish(order_events)
        return ApplicationOperationResultDto.of(application, tuple(order_events))
