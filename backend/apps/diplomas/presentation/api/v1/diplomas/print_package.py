"""Print-package composition: per-nomination summary, target resolution, jobs.

A competition assigns a template per nomination, so generation is scoped to
nominations: the summary reports each nomination's template + counts, and a run
targets all assigned nominations or a chosen subset. Keeps the views thin.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.application.batch_services import DiplomaBatchGenerationService, NominationTarget
from apps.diplomas.domain.exceptions import PrintJobNotFoundError, PrintTemplateNotReadyError
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.models import (
    DiplomaModel,
    PrintJobModel,
    TemplateDocumentModel,
    TemplateModel,
)
from apps.diplomas.infrastructure.pdf.workspace import DjangoPrintPackageWorkspace
from apps.diplomas.infrastructure.repositories import DjangoDiplomaRepository
from apps.diplomas.presentation.api.v1.diplomas import composition

__all__ = [
    "build_batch_service",
    "get_print_job",
    "print_package_summary",
    "resolve_targets",
    "start_print_package",
]


def build_batch_service() -> DiplomaBatchGenerationService:
    return DiplomaBatchGenerationService(
        repository=DjangoDiplomaRepository(),
        snapshots=DjangoDiplomaSnapshotSource(),
        workspace=DjangoPrintPackageWorkspace(),
    )


def _assignments_by_category(competition_id: uuid.UUID) -> dict[str, dict[str, Any]]:
    """category_id -> {templateId, templateName} for the competition's assignments."""
    return {
        item["categoryId"]: item
        for item in composition.list_assignments()
        if item["competitionId"] == str(competition_id)
    }


def resolve_targets(
    competition_id: uuid.UUID, category_ids: list[str]
) -> list[NominationTarget]:
    """Turn requested nominations into (category, template) targets.

    Empty ``category_ids`` means every nomination with an assigned template.
    Nominations without an assignment are dropped.
    """
    assignments = _assignments_by_category(competition_id)
    selected = [str(cid) for cid in category_ids] if category_ids else list(assignments)
    targets: list[NominationTarget] = []
    for category_id in selected:
        assignment = assignments.get(category_id)
        if assignment is None:
            continue
        targets.append(
            NominationTarget(
                category_id=uuid.UUID(category_id),
                template_id=uuid.UUID(assignment["templateId"]),
            )
        )
    return targets


def print_package_summary(competition_id: uuid.UUID) -> dict[str, Any]:
    """Per-nomination stats: template, performances, existing diplomas, to-create."""
    assignments = _assignments_by_category(competition_id)
    # A nomination is only "ready" to generate when its template also has a PDF.
    assigned_template_ids = {item["templateId"] for item in assignments.values()}
    templates_with_pdf = {
        str(template_id)
        for template_id in TemplateDocumentModel.objects.filter(
            template__id__in=assigned_template_ids, deleted_at__isnull=True
        ).values_list("template_id", flat=True)
    }
    category_names = {
        str(row["id"]): str(row["name"])
        for row in CategoryModel.objects.filter(
            competition_id=competition_id, deleted_at__isnull=True
        ).values("id", "name")
    }
    diploma_submissions = {
        str(submission_id)
        for submission_id in DiplomaModel.objects.filter(
            competition_id=competition_id, deleted_at__isnull=True
        ).values_list("submission_id", flat=True)
    }

    counts: dict[str, dict[str, int]] = {}
    from apps.applications.infrastructure.models.submission import SubmissionModel

    for row in SubmissionModel.objects.filter(
        competition_id=competition_id, deleted_at__isnull=True
    ).values("id", "performance"):
        category_id = str((row["performance"] or {}).get("nomination_id") or "")
        if not category_id:
            continue
        bucket = counts.setdefault(category_id, {"submissions": 0, "existing": 0})
        bucket["submissions"] += 1
        if str(row["id"]) in diploma_submissions:
            bucket["existing"] += 1

    nominations: list[dict[str, Any]] = []
    for category_id in set(counts) | set(assignments):
        assignment = assignments.get(category_id)
        stats = counts.get(category_id, {"submissions": 0, "existing": 0})
        ready = assignment is not None and assignment["templateId"] in templates_with_pdf
        nominations.append(
            {
                "categoryId": category_id,
                "nomination": category_names.get(category_id),
                "templateId": assignment["templateId"] if assignment else None,
                "templateName": assignment["templateName"] if assignment else None,
                # Assigned but with no uploaded PDF yet — cannot generate.
                "ready": ready,
                "submissions": stats["submissions"],
                "existing": stats["existing"],
                "willCreate": max(0, stats["submissions"] - stats["existing"]) if ready else 0,
            }
        )
    nominations.sort(key=lambda item: (item["nomination"] or "").lower())
    return {"competitionId": str(competition_id), "nominations": nominations}


def _job_json(job: PrintJobModel) -> dict[str, Any]:
    return {
        "jobId": str(job.id),
        "competitionId": str(job.competition_id),
        "categoryIds": [str(cid) for cid in (job.category_ids or [])],
        "force": job.force,
        "status": job.status,
        "created": job.created_count,
        "skipped": job.skipped_count,
        "zipUrl": job.zip_path or None,
        "error": job.error or None,
        "createdAt": job.created_at,
        "updatedAt": job.updated_at,
    }


def start_print_package(
    *, competition_id: uuid.UUID, category_ids: list[str], force: bool = False
) -> dict[str, Any]:
    """Create + enqueue a print-package job for the chosen nominations (or all).

    ``force`` re-renders print PDFs for diplomas that already have one. Validates
    that the resolved nominations have a template with a PDF.
    """
    targets = resolve_targets(competition_id, category_ids)
    if not targets:
        raise PrintTemplateNotReadyError("No nomination with an assigned template to generate.")
    for target in targets:
        if not TemplateModel.objects.filter(
            id=target.template_id, deleted_at__isnull=True
        ).exists():
            raise PrintTemplateNotReadyError("A selected template was not found.")
        if not TemplateDocumentModel.objects.filter(
            template__id=target.template_id, deleted_at__isnull=True
        ).exists():
            raise PrintTemplateNotReadyError("A selected template has no PDF to print over.")

    job = PrintJobModel.objects.create(
        competition_id=competition_id,
        category_ids=[str(cid) for cid in category_ids],
        force=force,
    )
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
