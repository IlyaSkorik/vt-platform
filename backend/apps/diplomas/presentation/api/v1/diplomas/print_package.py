"""Print-package composition: wire the batch service and manage its jobs.

Keeps the views thin — validates inputs, creates and enqueues the durable job,
and shapes job status into the API payload.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.diplomas.application.batch_services import DiplomaBatchGenerationService
from apps.diplomas.domain.exceptions import (
    PrintJobNotFoundError,
    PrintTemplateNotReadyError,
    TemplateNotFoundError,
)
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.models import (
    PrintJobModel,
    TemplateDocumentModel,
    TemplateModel,
)
from apps.diplomas.infrastructure.pdf.workspace import DjangoPrintPackageWorkspace
from apps.diplomas.infrastructure.repositories import DjangoDiplomaRepository

__all__ = ["build_batch_service", "get_print_job", "start_print_package"]


def build_batch_service() -> DiplomaBatchGenerationService:
    return DiplomaBatchGenerationService(
        repository=DjangoDiplomaRepository(),
        snapshots=DjangoDiplomaSnapshotSource(),
        workspace=DjangoPrintPackageWorkspace(),
    )


def _job_json(job: PrintJobModel) -> dict[str, Any]:
    return {
        "jobId": str(job.id),
        "competitionId": str(job.competition_id),
        "templateId": str(job.template_id),
        "status": job.status,
        "created": job.created_count,
        "skipped": job.skipped_count,
        "zipUrl": job.zip_path or None,
        "error": job.error or None,
        "createdAt": job.created_at,
        "updatedAt": job.updated_at,
    }


def start_print_package(*, competition_id: uuid.UUID, template_id: uuid.UUID) -> dict[str, Any]:
    """Create + enqueue a print-package job. Raises on unknown/not-ready template."""
    if not TemplateModel.objects.filter(id=template_id, deleted_at__isnull=True).exists():
        raise TemplateNotFoundError("Template was not found.")
    if not TemplateDocumentModel.objects.filter(
        template__id=template_id, deleted_at__isnull=True
    ).exists():
        raise PrintTemplateNotReadyError("The template has no PDF to print over.")

    job = PrintJobModel.objects.create(competition_id=competition_id, template_id=template_id)
    # Enqueue after the row is committed; under eager mode this runs inline.
    from apps.diplomas.tasks import generate_print_package

    generate_print_package.delay(str(job.id))
    job.refresh_from_db()
    return _job_json(job)


def get_print_job(job_id: uuid.UUID) -> dict[str, Any]:
    """One job's status/result. Raises :class:`PrintJobNotFoundError` if unknown."""
    job = PrintJobModel.objects.filter(id=job_id).first()
    if job is None:
        raise PrintJobNotFoundError("Print job was not found.")
    return _job_json(job)
