"""Composition root for the Submission attachment endpoints.

Wires the upload/remove-attachment use cases to their concrete adapters: the
submission repository, the file storage backend, the competition upload-policy ACL,
the clock, the uuid source and the event publisher.
"""

from __future__ import annotations

from apps.applications.application.commands.attachments import RemoveAttachmentHandler, UploadAttachmentHandler
from apps.applications.application.commands.participants import AddParticipantHandler, RemoveParticipantHandler
from apps.applications.application.commands.performance import SetPerformanceHandler
from apps.applications.application.commands.pricing import CalculatePriceHandler
from apps.applications.application.commands.teachers import AddTeacherHandler, RemoveTeacherHandler
from apps.applications.application.queries.get_submission import GetSubmissionHandler
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
    "build_add_participant_handler",
    "build_add_teacher_handler",
    "build_calculate_price_handler",
    "build_get_submission_handler",
    "build_remove_attachment_handler",
    "build_remove_participant_handler",
    "build_remove_teacher_handler",
    "build_set_performance_handler",
    "build_upload_attachment_handler",
]


def _submissions() -> DjangoSubmissionRepository:
    return DjangoSubmissionRepository()


def build_get_submission_handler() -> GetSubmissionHandler:
    return GetSubmissionHandler(submissions=_submissions(), organization=DjangoOrganizationReadModel())


def build_set_performance_handler() -> SetPerformanceHandler:
    return SetPerformanceHandler(submissions=_submissions(), clock=SystemClock(), events=NullEventPublisher())


def build_add_participant_handler() -> AddParticipantHandler:
    return AddParticipantHandler(submissions=_submissions(), clock=SystemClock(), uuids=Uuid7Generator(), events=NullEventPublisher())


def build_remove_participant_handler() -> RemoveParticipantHandler:
    return RemoveParticipantHandler(submissions=_submissions(), clock=SystemClock(), events=NullEventPublisher())


def build_add_teacher_handler() -> AddTeacherHandler:
    return AddTeacherHandler(submissions=_submissions(), clock=SystemClock(), uuids=Uuid7Generator(), events=NullEventPublisher())


def build_remove_teacher_handler() -> RemoveTeacherHandler:
    return RemoveTeacherHandler(submissions=_submissions(), clock=SystemClock(), events=NullEventPublisher())


def build_calculate_price_handler() -> CalculatePriceHandler:
    return CalculatePriceHandler(submissions=_submissions(), catalog=DjangoCompetitionCatalog(), clock=SystemClock(), events=NullEventPublisher())


def build_upload_attachment_handler() -> UploadAttachmentHandler:
    return UploadAttachmentHandler(
        submissions=DjangoSubmissionRepository(),
        storage=DjangoFileStorage(),
        upload_policy=DjangoCompetitionUploadPolicy(),
        clock=SystemClock(),
        uuids=Uuid7Generator(),
        events=NullEventPublisher(),
    )


def build_remove_attachment_handler() -> RemoveAttachmentHandler:
    return RemoveAttachmentHandler(submissions=DjangoSubmissionRepository(), clock=SystemClock(), events=NullEventPublisher())
