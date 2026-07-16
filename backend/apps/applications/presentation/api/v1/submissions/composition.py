"""Composition root for the Submission attachment endpoints.

Wires the upload/remove-attachment use cases to their concrete adapters: the
submission repository, the file storage backend, the competition upload-policy ACL,
the clock, the uuid source and the event publisher.
"""

from __future__ import annotations

from apps.applications.application.commands.attachments import RemoveAttachmentHandler, UploadAttachmentHandler
from apps.applications.application.commands.cancel import CancelSubmissionByReviewerHandler
from apps.applications.application.commands.participants import AddParticipantHandler, RemoveParticipantHandler
from apps.applications.application.commands.payment import (
    AcceptSubmissionHandler,
    CompleteSubmissionHandler,
    MarkPaidHandler,
    MarkWaitingPaymentHandler,
    ScheduleSubmissionHandler,
)
from apps.applications.application.commands.performance import SetPerformanceHandler
from apps.applications.application.commands.pricing import CalculatePriceHandler
from apps.applications.application.commands.review import (
    ApproveSubmissionHandler,
    ReturnSubmissionForCorrectionHandler,
    StartReviewHandler,
)
from apps.applications.application.commands.teachers import AddTeacherHandler, RemoveTeacherHandler
from apps.applications.application.queries.get_submission import GetSubmissionHandler
from apps.applications.application.queries.list_submissions import ListCompetitionSubmissionsHandler
from apps.applications.infrastructure.acl import (
    DjangoCompetitionCatalog,
    DjangoCompetitionUploadPolicy,
    DjangoOrganizationReadModel,
)
from apps.applications.infrastructure.messaging import NullEventPublisher
from apps.applications.infrastructure.repositories import DjangoSubmissionRepository
from apps.applications.infrastructure.storage import DjangoFileStorage
from apps.applications.infrastructure.system import SystemClock, Uuid7Generator

__all__ = [
    "build_accept_submission_handler",
    "build_add_participant_handler",
    "build_add_teacher_handler",
    "build_approve_submission_handler",
    "build_calculate_price_handler",
    "build_cancel_submission_by_reviewer_handler",
    "build_complete_submission_handler",
    "build_get_submission_handler",
    "build_list_competition_submissions_handler",
    "build_mark_paid_handler",
    "build_mark_waiting_payment_handler",
    "build_remove_attachment_handler",
    "build_remove_participant_handler",
    "build_remove_teacher_handler",
    "build_return_for_correction_handler",
    "build_schedule_submission_handler",
    "build_set_performance_handler",
    "build_start_review_handler",
    "build_upload_attachment_handler",
]


def _submissions() -> DjangoSubmissionRepository:
    return DjangoSubmissionRepository()


def build_get_submission_handler() -> GetSubmissionHandler:
    return GetSubmissionHandler(submissions=_submissions(), organization=DjangoOrganizationReadModel())


def build_list_competition_submissions_handler() -> ListCompetitionSubmissionsHandler:
    return ListCompetitionSubmissionsHandler(submissions=_submissions(), organization=DjangoOrganizationReadModel())


def build_set_performance_handler() -> SetPerformanceHandler:
    return SetPerformanceHandler(
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_add_participant_handler() -> AddParticipantHandler:
    return AddParticipantHandler(
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=NullEventPublisher(),
    )


def build_remove_participant_handler() -> RemoveParticipantHandler:
    return RemoveParticipantHandler(
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_add_teacher_handler() -> AddTeacherHandler:
    return AddTeacherHandler(
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=NullEventPublisher(),
    )


def build_remove_teacher_handler() -> RemoveTeacherHandler:
    return RemoveTeacherHandler(
        submissions=_submissions(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_calculate_price_handler() -> CalculatePriceHandler:
    return CalculatePriceHandler(submissions=_submissions(), catalog=DjangoCompetitionCatalog(), clock=SystemClock(), events=NullEventPublisher())


def build_upload_attachment_handler() -> UploadAttachmentHandler:
    return UploadAttachmentHandler(
        submissions=DjangoSubmissionRepository(),
        storage=DjangoFileStorage(),
        upload_policy=DjangoCompetitionUploadPolicy(),
        catalog=DjangoCompetitionCatalog(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=NullEventPublisher(),
    )


def build_remove_attachment_handler() -> RemoveAttachmentHandler:
    return RemoveAttachmentHandler(submissions=DjangoSubmissionRepository(), clock=SystemClock(), events=NullEventPublisher())


def build_start_review_handler() -> StartReviewHandler:
    return StartReviewHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_return_for_correction_handler() -> ReturnSubmissionForCorrectionHandler:
    return ReturnSubmissionForCorrectionHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=NullEventPublisher(),
    )


def build_approve_submission_handler() -> ApproveSubmissionHandler:
    return ApproveSubmissionHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_mark_waiting_payment_handler() -> MarkWaitingPaymentHandler:
    return MarkWaitingPaymentHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_mark_paid_handler() -> MarkPaidHandler:
    return MarkPaidHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_accept_submission_handler() -> AcceptSubmissionHandler:
    return AcceptSubmissionHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_schedule_submission_handler() -> ScheduleSubmissionHandler:
    return ScheduleSubmissionHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_complete_submission_handler() -> CompleteSubmissionHandler:
    return CompleteSubmissionHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )


def build_cancel_submission_by_reviewer_handler() -> CancelSubmissionByReviewerHandler:
    return CancelSubmissionByReviewerHandler(
        submissions=_submissions(),
        organization=DjangoOrganizationReadModel(),
        clock=SystemClock(),
        events=NullEventPublisher(),
    )
