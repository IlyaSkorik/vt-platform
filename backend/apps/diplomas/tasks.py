"""Celery tasks for the Diplomas bounded context (autodiscovered by name).

Thin: resolve the framework-free use case from the composition root and run it,
recording progress on the durable :class:`PrintJobModel` so the client can poll.
"""

from __future__ import annotations

from celery import shared_task


@shared_task(name="diplomas.generate_print_package")
def generate_print_package(job_id: str) -> None:
    """Run one print-package job: create missing diplomas, render PDFs, build ZIP."""
    from django.utils import timezone

    from apps.diplomas.domain.document_types import DocumentType
    from apps.diplomas.infrastructure.models import PrintJobModel, PrintJobStatusChoices
    from apps.diplomas.presentation.api.v1.diplomas import archive
    from apps.diplomas.presentation.api.v1.diplomas.print_package import (
        build_batch_service,
        resolve_targets,
    )

    job = PrintJobModel.objects.filter(id=job_id).first()
    if job is None:
        return

    job.status = PrintJobStatusChoices.RUNNING
    job.updated_at = timezone.now()
    job.save(update_fields=["status", "updated_at"])

    try:
        targets = resolve_targets(job.competition_id, job.category_ids or [])
        result = build_batch_service().generate_print_package(
            competition_id=job.competition_id, targets=targets, now=timezone.now(), force=job.force
        )
    except Exception as exc:
        job.status = PrintJobStatusChoices.FAILED
        job.error = str(exc)[:2000]
    else:
        job.status = PrintJobStatusChoices.COMPLETED
        job.created_count = result.created
        job.skipped_count = result.skipped
        job.zip_path = result.zip_path
        job.error = ""
        # The archive records the run, not the job: the resolved targets rather than
        # the request's (possibly empty, meaning "all") selection, and the whole
        # package rather than the diplomas this run happened to create — that is what
        # the ZIP contains and what the organizer prints.
        archive.record_run(
            competition_id=job.competition_id,
            document_type=DocumentType.DIPLOMA.value,
            category_ids=[str(target.category_id) for target in targets],
            document_count=result.created + result.skipped,
            created_count=result.created,
            zip_path=result.zip_path,
            actor_id=job.actor_id,
            actor_label=job.actor_label,
        )

    job.updated_at = timezone.now()
    job.version += 1
    job.save()
