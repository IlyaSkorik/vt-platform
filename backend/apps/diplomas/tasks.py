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

    from apps.diplomas.infrastructure.models import PrintJobModel, PrintJobStatusChoices
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
            competition_id=job.competition_id, targets=targets, now=timezone.now()
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

    job.updated_at = timezone.now()
    job.version += 1
    job.save()
