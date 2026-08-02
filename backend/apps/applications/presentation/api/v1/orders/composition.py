"""Composition root for the Application (order) API edge.

The one place where the framework-free order use cases are wired to their concrete
infrastructure adapters (ARCH-001 §7.3): the two repositories, the Competition /
Identity / educational-organization ACLs, the clock, the uuid source and the event
publisher. Views ask this module for a fully-assembled handler and stay ignorant of
which adapter sits behind each port. Adapters are stateless and cheap, so handlers
are assembled per request.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings

from apps.applications.application.orders import (
    AddSubmissionToApplicationHandler,
    AutoCancelUnpaidApplicationHandler,
    CancelApplicationHandler,
    CompleteApplicationHandler,
    CreateApplicationHandler,
    GetApplicationHandler,
    ListApplicationsHandler,
    ListDraftApplicationsHandler,
    MarkApplicationPaidHandler,
    RecordConsentsHandler,
    RemoveAdditionalServiceHandler,
    RemoveApplicationReceiptHandler,
    RemoveSubmissionFromApplicationHandler,
    RequestApplicationPaymentHandler,
    SelectAdditionalServiceHandler,
    SelectEducationalOrganizationHandler,
    SubmitApplicationHandler,
    UploadApplicationReceiptHandler,
)
from apps.applications.infrastructure.acl import (
    DjangoCompetitionCatalog,
    DjangoCompetitionServiceCatalog,
    DjangoEducationalOrganizationDirectory,
    DjangoIdentityReadModel,
    DjangoParticipantGuardianRegistry,
)
from apps.applications.infrastructure.messaging import (
    DjangoApplicantNotifier,
    NullEventPublisher,
)
from apps.applications.infrastructure.repositories import DjangoApplicationRepository, DjangoSubmissionRepository
from apps.applications.infrastructure.storage import DjangoFileStorage
from apps.applications.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_add_submission_handler",
    "build_auto_cancel_unpaid_handler",
    "build_cancel_application_handler",
    "build_complete_application_handler",
    "build_create_application_handler",
    "build_get_application_handler",
    "build_list_applications_handler",
    "build_list_drafts_handler",
    "build_mark_paid_handler",
    "build_record_consents_handler",
    "build_remove_receipt_handler",
    "build_remove_service_handler",
    "build_remove_submission_handler",
    "build_request_payment_handler",
    "build_select_educational_organization_handler",
    "build_select_service_handler",
    "build_submit_application_handler",
    "build_upload_receipt_handler",
]


def _applications() -> DjangoApplicationRepository:
    return DjangoApplicationRepository()


def _submissions() -> DjangoSubmissionRepository:
    return DjangoSubmissionRepository()


def build_create_application_handler() -> CreateApplicationHandler:
    return CreateApplicationHandler(
        applications=_applications(),
        catalog=DjangoCompetitionCatalog(),
        identity=DjangoIdentityReadModel(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
    )


def build_add_submission_handler() -> AddSubmissionToApplicationHandler:
    return AddSubmissionToApplicationHandler(
        applications=_applications(),
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=NullEventPublisher(),
    )


def build_remove_submission_handler() -> RemoveSubmissionFromApplicationHandler:
    return RemoveSubmissionFromApplicationHandler(
        applications=_applications(),
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_select_service_handler() -> SelectAdditionalServiceHandler:
    return SelectAdditionalServiceHandler(
        applications=_applications(),
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        services=DjangoCompetitionServiceCatalog(),
        clock=SystemClock(),
    )


def build_remove_service_handler() -> RemoveAdditionalServiceHandler:
    return RemoveAdditionalServiceHandler(applications=_applications(), catalog=DjangoCompetitionCatalog(), clock=SystemClock())


def build_record_consents_handler() -> RecordConsentsHandler:
    return RecordConsentsHandler(applications=_applications(), catalog=DjangoCompetitionCatalog(), clock=SystemClock())


def build_select_educational_organization_handler() -> SelectEducationalOrganizationHandler:
    return SelectEducationalOrganizationHandler(
        applications=_applications(),
        catalog=DjangoCompetitionCatalog(),
        directory=DjangoEducationalOrganizationDirectory(),
        clock=SystemClock(),
    )


def build_submit_application_handler() -> SubmitApplicationHandler:
    return SubmitApplicationHandler(
        applications=_applications(),
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        services=DjangoCompetitionServiceCatalog(),
        clock=SystemClock(),
        events=NullEventPublisher(),
        identity=DjangoIdentityReadModel(),
        notifier=DjangoApplicantNotifier(),
        payment_window=timedelta(hours=settings.APPLICATION_PAYMENT_WINDOW_HOURS),
        guardians=DjangoParticipantGuardianRegistry(),
    )


def build_auto_cancel_unpaid_handler() -> AutoCancelUnpaidApplicationHandler:
    return AutoCancelUnpaidApplicationHandler(
        applications=_applications(),
        submissions=_submissions(),
        clock=SystemClock(),
        events=NullEventPublisher(),
        identity=DjangoIdentityReadModel(),
        notifier=DjangoApplicantNotifier(),
    )


def build_request_payment_handler() -> RequestApplicationPaymentHandler:
    return RequestApplicationPaymentHandler(applications=_applications(), submissions=_submissions(), clock=SystemClock())


def build_mark_paid_handler() -> MarkApplicationPaidHandler:
    return MarkApplicationPaidHandler(
        applications=_applications(),
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        events=NullEventPublisher(),
        services=DjangoCompetitionServiceCatalog(),
    )


def build_complete_application_handler() -> CompleteApplicationHandler:
    return CompleteApplicationHandler(applications=_applications(), clock=SystemClock())


def build_cancel_application_handler() -> CancelApplicationHandler:
    return CancelApplicationHandler(applications=_applications(), submissions=_submissions(), clock=SystemClock(), events=NullEventPublisher())


def build_upload_receipt_handler() -> UploadApplicationReceiptHandler:
    return UploadApplicationReceiptHandler(
        applications=_applications(), storage=DjangoFileStorage(), clock=SystemClock(), events=NullEventPublisher()
    )


def build_remove_receipt_handler() -> RemoveApplicationReceiptHandler:
    return RemoveApplicationReceiptHandler(applications=_applications(), clock=SystemClock(), events=NullEventPublisher())


def build_get_application_handler() -> GetApplicationHandler:
    return GetApplicationHandler(
        applications=_applications(),
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
    )


def build_list_applications_handler() -> ListApplicationsHandler:
    return ListApplicationsHandler(
        applications=_applications(),
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
    )


def build_list_drafts_handler() -> ListDraftApplicationsHandler:
    return ListDraftApplicationsHandler(
        applications=_applications(),
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
    )
