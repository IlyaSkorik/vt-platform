"""Read/write helpers for the non-registry document REST surface.

Keeps the views thin: wires the composition root's
:class:`IssuedDocumentGenerationService` to the request, aggregates the
per-nomination outcomes into one summary, and owns the job row the run is
reported through.

**The run is a job, not a request.** It was synchronous while the reasoning was
"a thank-you run has no number to reserve, so there is nothing to serialize" —
true, and beside the point: the run renders a PDF per recipient and uploads a
ZIP, and a festival-sized one takes minutes. Nothing in the chain will hold a
connection open that long. nginx returned 504 while the worker went on to finish
the run, so the documents existed and the organizer was told the opposite.

So the request now does what the print package's does — refuse what it can
refuse, queue the work, hand back a job to poll — and :func:`generate_documents`
below is unchanged, called by the worker instead of by the view.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.utils import timezone

from apps.diplomas.composition import build_issued_document_generation_service
from apps.diplomas.domain.document_types import DocumentType, policy_for
from apps.diplomas.domain.exceptions import DocumentJobNotFoundError, TemplateTypeMismatchError
from apps.diplomas.infrastructure.models import DocumentJobModel
from apps.diplomas.presentation.api.v1.diplomas import archive

__all__ = ["generate_documents", "get_document_job", "start_document_generation"]


def generate_documents(
    *,
    competition_id: uuid.UUID,
    category_ids: list[uuid.UUID],
    document_type: str,
    force: bool = False,
    bundle: bool = False,
    publish: bool = True,
    actor_id: uuid.UUID | None = None,
    actor_label: str = "",
) -> dict[str, Any]:
    """Generate one kind of document across the chosen nominations.

    Each genre is generated from **its own** assigned template, and each of its
    nominations from theirs where they have one — so the run honours per-genre and
    per-nomination designs rather than one competition-wide letter. May raise a
    ``DiplomaError`` (genre with no template at all, wrong template kind, template
    with no PDF) — the first failing genre aborts the run. Entries whose nomination
    resolves to no template are counted in ``withoutTemplate``, not raised over.

    Two independent switches, because the organizer's two intents are independent:
    ``publish`` shows the documents to the participants, ``bundle`` hands back a ZIP
    to print from (in ``zipUrl``). Preparing a print run therefore leaves the
    cabinets untouched, and a later publishing run publishes what it finds without
    re-rendering it. Publication is never withdrawn by a subsequent run.
    """
    service = build_issued_document_generation_service()
    kind = DocumentType(document_type)
    now = timezone.now()

    created = 0
    regenerated = 0
    without_recipient = 0
    without_template = 0
    published = 0
    items: list[tuple[str, str]] = []
    for category_id in category_ids:
        result = service.generate_for_nomination(
            competition_id=competition_id,
            category_id=category_id,
            document_type=kind,
            now=now,
            force=force,
            publish=publish,
        )
        created += result.created
        regenerated += result.regenerated
        without_recipient += result.without_recipient
        without_template += result.without_template
        published += result.published
        items.extend(result.items)

    # No documents at all means nothing to print: an empty archive would only give
    # the organizer a broken download to puzzle over.
    zip_url = service.bundle(competition_id=competition_id, document_type=kind, items=items) if bundle and items else None

    # One line of history per run, for the archive the organizer re-downloads from.
    archive.record_run(
        competition_id=competition_id,
        document_type=kind.value,
        category_ids=[str(category_id) for category_id in category_ids],
        document_count=len(items),
        created_count=created,
        published_count=published,
        zip_path=zip_url or "",
        actor_id=actor_id,
        actor_label=actor_label,
    )

    return {
        "documentType": kind.value,
        "created": created,
        "regenerated": regenerated,
        "withoutRecipient": without_recipient,
        "withoutTemplate": without_template,
        "nominations": len(category_ids),
        "documents": len(items),
        "published": published,
        "zipUrl": zip_url,
    }


def _job_json(job: DocumentJobModel) -> dict[str, Any]:
    """One job as the client polls it.

    ``result`` is the very summary the endpoint used to answer with, so the page
    that renders a finished run did not have to learn a new shape — only to wait
    for it. Absent until the run completes, and absent for good on a failure,
    where ``error`` carries what went wrong instead.
    """
    return {
        "jobId": str(job.id),
        "competitionId": str(job.competition_id),
        "categoryIds": [str(category_id) for category_id in (job.category_ids or [])],
        "documentType": job.document_type,
        "force": job.force,
        "bundle": job.bundle,
        "publish": job.publish,
        "status": job.status,
        "result": job.result or None,
        "error": job.error or None,
        "createdAt": job.created_at,
        "updatedAt": job.updated_at,
    }


def start_document_generation(
    *,
    competition_id: uuid.UUID,
    category_ids: list[uuid.UUID],
    document_type: str,
    force: bool = False,
    bundle: bool = False,
    publish: bool = True,
    actor_id: uuid.UUID | None = None,
    actor_label: str = "",
) -> dict[str, Any]:
    """Queue a generation run for the chosen genres; return the job to poll.

    The kind is validated here rather than in the worker, because a request is
    the last place with somebody to answer: a diploma routed to this endpoint is
    a mistake the caller can still be told about, while the same mistake inside a
    worker is a failed job nobody asked for. Everything the run can only discover
    once it starts — a genre with no template, a template with no PDF — stays the
    worker's to report, on the job.

    The actor is recorded on the job because only the request knows who asked;
    the worker carries it into the generation archive once the run completes.
    """
    kind = DocumentType(document_type)
    policy = policy_for(kind)
    if policy.is_registry_document or policy.numbered:
        # A numbered, verifiable kind is the Diploma aggregate's and goes through
        # the print package, which reserves its numbers. The service refuses it
        # too, but by then the caller is a worker and the refusal is a dead job.
        raise TemplateTypeMismatchError("Документы реестра выпускаются из пакета печати дипломов.")

    job = DocumentJobModel.objects.create(
        competition_id=competition_id,
        category_ids=[str(category_id) for category_id in category_ids],
        document_type=kind.value,
        force=force,
        bundle=bundle,
        publish=publish,
        actor_id=actor_id,
        actor_label=actor_label,
    )
    from apps.diplomas.tasks import generate_documents as run_job

    run_job.delay(str(job.id))
    job.refresh_from_db()
    return _job_json(job)


def get_document_job(job_id: uuid.UUID) -> dict[str, Any]:
    """One job's status and result. Raises :class:`DocumentJobNotFoundError` if unknown."""
    job = DocumentJobModel.objects.filter(id=job_id).first()
    if job is None:
        raise DocumentJobNotFoundError("Задание на формирование документов не найдено.")
    return _job_json(job)
