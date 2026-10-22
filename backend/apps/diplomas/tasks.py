"""Celery tasks for the Diplomas bounded context (autodiscovered by name).

Thin: resolve the framework-free use case from the composition root and run it,
recording progress on a durable job row (:class:`PrintJobModel` for the numbered
print package, :class:`DocumentJobModel` for every other kind) so the client can
poll it. Both runs render a PDF per document and upload an archive, which is more
work than any proxy will hold a connection open for.
"""

from __future__ import annotations

import uuid

from celery import shared_task


@shared_task(name="diplomas.generate_print_package")  # type: ignore[untyped-decorator]  # celery ships no stubs
def generate_print_package(job_id: str) -> None:
    """Run one print-package job: create missing diplomas, render PDFs, build ZIP."""
    from django.utils import timezone

    from apps.diplomas.domain.document_types import DocumentType
    from apps.diplomas.infrastructure.models import PrintJobModel, PrintJobStatusChoices
    from apps.diplomas.presentation.api.v1.diplomas import archive
    from apps.diplomas.presentation.api.v1.diplomas.print_package import (
        build_batch_service,
        printable_targets,
    )

    job = PrintJobModel.objects.filter(id=job_id).first()
    if job is None:
        return

    job.status = PrintJobStatusChoices.RUNNING
    job.updated_at = timezone.now()
    job.save(update_fields=["status", "updated_at"])

    try:
        targets = printable_targets(job.competition_id, job.category_ids or [])
        result = build_batch_service(job.competition_id).generate_print_package(
            competition_id=job.competition_id,
            targets=targets,
            now=timezone.now(),
            force=job.force,
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


@shared_task(name="diplomas.generate_documents")  # type: ignore[untyped-decorator]  # celery ships no stubs
def generate_documents(job_id: str) -> None:
    """Run one non-registry generation job: render each document, bundle if asked.

    Asynchronous for the same reason the print package is, and for no other: the
    run renders a PDF per recipient and uploads an archive, which outlasts what a
    proxy will hold a connection open for. Nothing about *what* it does changed —
    the use case is the one the endpoint used to call inline, and its summary is
    stored whole on the job.
    """
    from django.utils import timezone

    from apps.diplomas.infrastructure.models import DocumentJobModel, PrintJobStatusChoices
    from apps.diplomas.presentation.api.v1.diplomas import documents

    job = DocumentJobModel.objects.filter(id=job_id).first()
    if job is None:
        return

    job.status = PrintJobStatusChoices.RUNNING
    job.updated_at = timezone.now()
    job.save(update_fields=["status", "updated_at"])

    try:
        summary = documents.generate_documents(
            competition_id=job.competition_id,
            category_ids=[uuid.UUID(str(category_id)) for category_id in (job.category_ids or [])],
            document_type=job.document_type,
            force=job.force,
            bundle=job.bundle,
            publish=job.publish,
            actor_id=job.actor_id,
            actor_label=job.actor_label,
        )
    except Exception as exc:
        job.status = PrintJobStatusChoices.FAILED
        # The organizer sees this string and nothing else about the failure, so a
        # domain error's own wording ("этому жанру не назначен шаблон") is worth
        # more here than a generic line would be.
        job.error = str(exc)[:2000]
    else:
        job.status = PrintJobStatusChoices.COMPLETED
        job.result = summary
        job.error = ""

    job.updated_at = timezone.now()
    job.version += 1
    job.save()
