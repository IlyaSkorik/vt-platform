"""Print-package composition: per-nomination summary, target resolution, jobs.

A competition assigns a template per nomination **per document type**, so
generation is scoped to nominations: the summary reports every type's template +
counts for each nomination, and a run targets all assigned nominations or a chosen
subset. The summary serves both generation actions; the run here is the numbered
print package, so it resolves diploma assignments only. Keeps the views thin.
"""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.application.batch_services import DiplomaBatchGenerationService, NominationTarget
from apps.diplomas.application.numbering import DiplomaNumberService
from apps.diplomas.domain.document_types import DocumentType, policy_for
from apps.diplomas.domain.exceptions import PrintJobNotFoundError, PrintTemplateNotReadyError
from apps.diplomas.infrastructure.acl import COMPETING_SUBMISSION_STATUSES, DjangoDiplomaSnapshotSource, awardable_degrees
from apps.diplomas.infrastructure.models import (
    DiplomaModel,
    IssuedDocumentModel,
    PrintJobModel,
    TemplateDocumentModel,
    TemplateModel,
)
from apps.diplomas.infrastructure.pdf.workspace import DjangoPrintPackageWorkspace
from apps.diplomas.infrastructure.repositories import (
    DjangoDiplomaNumberSequence,
    DjangoDiplomaRepository,
)
from apps.diplomas.presentation.api.v1.diplomas import composition
from apps.diplomas.presentation.scope import Scope

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
        numbers=DiplomaNumberService(sequence=DjangoDiplomaNumberSequence()),
        place_degrees=awardable_degrees(),
    )


def _assignments_by_category(competition_id: uuid.UUID, document_type: DocumentType) -> dict[str, dict[str, Any]]:
    """category_id -> assignment, for **one** document type of the competition.

    The type filter is load-bearing, not a convenience. Since document types
    landed, a nomination holds one assignment *per type*, so keying by category
    alone silently collapses its diploma and thank-you templates into whichever
    row happened to come last — and the survivor could be either kind.
    """
    wanted = document_type.value
    return {
        item["categoryId"]: item
        # Unscoped, and narrowed to `competition_id` on the next line instead. The
        # caller's right to this competition was settled at the edge, and half the
        # callers are Celery tasks with no request to scope by.
        for item in composition.list_assignments(scope=Scope.already_authorized())
        if item["competitionId"] == str(competition_id) and item["documentType"] == wanted
    }


def resolve_targets(competition_id: uuid.UUID, category_ids: list[str]) -> list[NominationTarget]:
    """Turn requested nominations into (category, template) targets.

    Empty ``category_ids`` means every nomination with an assigned template.
    Nominations without an assignment are dropped. Diplomas only: a nomination's
    thank-you template is never a print-package target.
    """
    assignments = _assignments_by_category(competition_id, DocumentType.DIPLOMA)
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


def _named_teachers(teachers: Any) -> int:
    """How many letters an entry's teacher roster is worth.

    Mirrors the snapshot source's rule — a teacher counts only once some part of
    the name is filled in — so the summary's forecast matches what a run actually
    issues rather than promising letters to blank rows.
    """
    count = 0
    for teacher in teachers or []:
        parts = (teacher.get("last_name"), teacher.get("first_name"), teacher.get("middle_name"))
        if any(str(part or "").strip() for part in parts):
            count += 1
    return count


def _named_members(participants: Any) -> int:
    """How many individual diplomas an entry's collective roster is worth.

    The **lead** participant's roster only, mirroring the snapshot source: an
    individual diploma names its member under the collective the diploma names, and
    that is the lead one.
    """
    rows = [row for row in participants or [] if isinstance(row, dict)]
    lead = next((row for row in rows if str(row.get("display_name") or "").strip()), rows[0] if rows else {})
    roster = lead.get("members")
    if not isinstance(roster, list):
        return 0
    return sum(1 for name in roster if str(name or "").strip())


def print_package_summary(competition_id: uuid.UUID) -> dict[str, Any]:
    """Per-nomination stats for **every** document type, one slot each.

    A nomination assigns a template per type, so readiness is per type too:
    «Вокал» may be ready to print diplomas and have no thank-you template at all.
    One merged flag cannot say that, and reporting one is what let the generation
    page offer nominations for a kind they had no template for.

    Each slot's forecast follows its own policy. A diploma is issued per
    performance, a thank-you letter per named teacher, an individual diploma per named
    member of a collective — three different denominators over the same entries. A
    per-teacher kind also reports the entries it cannot address at all.
    """
    assignments = {document_type: _assignments_by_category(competition_id, document_type) for document_type in DocumentType}
    # A slot is only "ready" to generate when its template also has a PDF.
    assigned_template_ids = {item["templateId"] for slots in assignments.values() for item in slots.values()}
    templates_with_pdf = {
        str(template_id)
        for template_id in TemplateDocumentModel.objects.filter(template__id__in=assigned_template_ids, deleted_at__isnull=True).values_list(
            "template_id", flat=True
        )
    }
    category_names = {
        str(row["id"]): str(row["name"])
        for row in CategoryModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).values("id", "name")
    }

    from apps.applications.infrastructure.models.submission import SubmissionModel

    category_of: dict[str, str] = {}
    submissions: Counter[str] = Counter()
    recipients: Counter[str] = Counter()
    unaddressable: Counter[str] = Counter()
    members: Counter[str] = Counter()
    # The same narrowing the generation pipeline applies, so «Выступлений» is the
    # number a run will actually walk rather than every entry ever filed.
    for row in SubmissionModel.objects.filter(
        competition_id=competition_id,
        deleted_at__isnull=True,
        status__in=COMPETING_SUBMISSION_STATUSES,
    ).values("id", "performance", "teachers", "participants"):
        category_id = str((row["performance"] or {}).get("nomination_id") or "")
        if not category_id:
            continue
        category_of[str(row["id"])] = category_id
        submissions[category_id] += 1
        named = _named_teachers(row["teachers"])
        recipients[category_id] += named
        if not named:
            unaddressable[category_id] += 1
        members[category_id] += _named_members(row["participants"])

    existing: dict[DocumentType, Counter[str]] = {kind: Counter() for kind in DocumentType}
    for raw_type, submission_id in DiplomaModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).values_list(
        "document_type", "submission_id"
    ):
        issued_in = category_of.get(str(submission_id))
        if issued_in is None:
            continue
        try:
            # Scoped by kind: the register now holds individual diplomas too, and
            # counting them as the collective's would report a nomination as done
            # before a single collective sheet existed.
            existing[DocumentType(raw_type)][issued_in] += 1
        except ValueError:  # pragma: no cover - a type the enum no longer knows
            continue
    for raw_type, submission_id in IssuedDocumentModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).values_list(
        "document_type", "submission_id"
    ):
        issued_in = category_of.get(str(submission_id))
        if issued_in is None:
            continue
        try:
            existing[DocumentType(raw_type)][issued_in] += 1
        except ValueError:  # pragma: no cover - a type the enum no longer knows
            continue

    def slot(document_type: DocumentType, category_id: str) -> dict[str, Any]:
        assignment = assignments[document_type].get(category_id)
        ready = assignment is not None and assignment["templateId"] in templates_with_pdf
        policy = policy_for(document_type)
        per_teacher = policy.per_teacher
        if per_teacher:
            total = recipients[category_id]
        elif policy.per_member:
            # One per person the applicants named, not one per entry: an ensemble that
            # named nobody contributes nothing to this slot.
            total = members[category_id]
        else:
            total = submissions[category_id]
        done = existing[document_type][category_id]
        return {
            "templateId": assignment["templateId"] if assignment else None,
            "templateName": assignment["templateName"] if assignment else None,
            # Assigned but with no uploaded PDF yet — cannot generate.
            "ready": ready,
            "existing": done,
            "willCreate": max(0, total - done) if ready else 0,
            # Entries a per-teacher kind cannot address; always 0 for the rest.
            "withoutRecipient": unaddressable[category_id] if per_teacher else 0,
        }

    # A nomination is listed when it has entries or a template of either kind.
    listed = set(submissions)
    for slots in assignments.values():
        listed |= set(slots)

    nominations: list[dict[str, Any]] = [
        {
            "categoryId": category_id,
            "nomination": category_names.get(category_id),
            "submissions": submissions[category_id],
            "diploma": slot(DocumentType.DIPLOMA, category_id),
            "individualDiploma": slot(DocumentType.INDIVIDUAL_DIPLOMA, category_id),
            "thankYou": slot(DocumentType.THANK_YOU, category_id),
        }
        for category_id in listed
    ]
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
    *,
    competition_id: uuid.UUID,
    category_ids: list[str],
    force: bool = False,
    actor_id: uuid.UUID | None = None,
    actor_label: str = "",
) -> dict[str, Any]:
    """Create + enqueue a print-package job for the chosen nominations (or all).

    ``force`` re-renders print PDFs for diplomas that already have one. Validates
    that the resolved nominations have a template with a PDF.

    The actor is recorded on the job because only the request knows who asked; the
    worker carries it into the generation archive once the run completes.
    """
    targets = resolve_targets(competition_id, category_ids)
    if not targets:
        raise PrintTemplateNotReadyError("Нет ни одной номинации с назначенным шаблоном.")
    for target in targets:
        if not TemplateModel.objects.filter(id=target.template_id, deleted_at__isnull=True).exists():
            raise PrintTemplateNotReadyError("Выбранный шаблон не найден.")
        if not TemplateDocumentModel.objects.filter(template__id=target.template_id, deleted_at__isnull=True).exists():
            raise PrintTemplateNotReadyError("У выбранного шаблона нет PDF-подложки для печати.")

    job = PrintJobModel.objects.create(
        competition_id=competition_id,
        category_ids=[str(cid) for cid in category_ids],
        force=force,
        actor_id=actor_id,
        actor_label=actor_label,
    )
    from apps.diplomas.tasks import generate_print_package

    generate_print_package.delay(str(job.id))
    job.refresh_from_db()
    return _job_json(job)


def get_print_job(job_id: uuid.UUID) -> dict[str, Any]:
    """One job's status/result. Raises :class:`PrintJobNotFoundError` if unknown."""
    job = PrintJobModel.objects.filter(id=job_id).first()
    if job is None:
        raise PrintJobNotFoundError("Задание на печать не найдено.")
    return _job_json(job)
