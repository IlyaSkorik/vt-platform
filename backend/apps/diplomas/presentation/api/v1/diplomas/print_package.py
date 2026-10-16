"""Print-package composition: per-genre summary, target resolution, jobs.

A competition assigns a template per genre **per document type**, and a genre's
nomination may assign one of its own, so generation is scoped to genres and
resolved inside them: the summary reports every type's template + counts for each
genre (and names the nominations that print on something else), while a run turns
the chosen genres into one target per template. The summary serves both generation
actions; the run here is the numbered print package, so it resolves diploma
assignments only. Keeps the views thin.
"""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from apps.competitions.infrastructure.models.taxonomy import CategoryModel, DisciplineModel
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
    "printable_targets",
    "resolve_targets",
    "start_print_package",
]


def build_batch_service(competition_id: uuid.UUID | None = None) -> DiplomaBatchGenerationService:
    """Assemble the batch service, with the festival's own award scale when known."""
    return DiplomaBatchGenerationService(
        repository=DjangoDiplomaRepository(),
        snapshots=DjangoDiplomaSnapshotSource(),
        workspace=DjangoPrintPackageWorkspace(),
        numbers=DiplomaNumberService(sequence=DjangoDiplomaNumberSequence()),
        place_degrees=awardable_degrees(competition_id),
    )


#: One genre's assignments of a single kind: ``None`` keys the genre's default,
#: a discipline id keys the nomination that prints on a template of its own.
type GenreSlots = dict[str | None, dict[str, Any]]


def _assignments_by_category(competition_id: uuid.UUID, document_type: DocumentType) -> dict[str, GenreSlots]:
    """category_id -> its assignments, for **one** document type of the competition.

    The type filter is load-bearing, not a convenience. Since document types
    landed, a nomination holds one assignment *per type*, so keying by category
    alone silently collapses its diploma and thank-you templates into whichever
    row happened to come last — and the survivor could be either kind.

    The second level keys by discipline for the same reason: a genre now holds a
    default *and* one row per nomination that overrides it, and flattening them
    would make which sheet an entry prints on depend on row order.
    """
    wanted = document_type.value
    by_category: dict[str, GenreSlots] = {}
    # Unscoped, and narrowed to `competition_id` below instead. The caller's right
    # to this competition was settled at the edge, and half the callers are Celery
    # tasks with no request to scope by.
    for item in composition.list_assignments(scope=Scope.already_authorized()):
        if item["competitionId"] != str(competition_id) or item["documentType"] != wanted:
            continue
        by_category.setdefault(str(item["categoryId"]), {})[item["disciplineId"]] = item
    return by_category


def _resolve_slot(slots: GenreSlots, discipline_id: str | None) -> dict[str, Any] | None:
    """The assignment an entry of this nomination prints on — its own, else the genre's."""
    if discipline_id is not None and (override := slots.get(discipline_id)) is not None:
        return override
    return slots.get(None)


def resolve_targets(competition_id: uuid.UUID, category_ids: list[str]) -> list[NominationTarget]:
    """Turn requested genres into the targets a print run walks.

    Empty ``category_ids`` means every genre with an assigned template. Genres
    without an assignment are dropped. Diplomas only: a thank-you template is never
    a print-package target.

    A genre with per-nomination templates becomes several targets — one per such
    nomination, plus one for the rest of the genre if it has a default. Between
    them they cover each entry exactly once, which is what keeps a festival that
    overrides one nomination from printing its diplomas twice.
    """
    assignments = _assignments_by_category(competition_id, DocumentType.DIPLOMA)
    selected = [str(cid) for cid in category_ids] if category_ids else list(assignments)
    targets: list[NominationTarget] = []
    for category_id in selected:
        slots = assignments.get(category_id)
        if not slots:
            continue
        overrides = {key: value for key, value in slots.items() if key is not None}
        for discipline_id, assignment in overrides.items():
            targets.append(
                NominationTarget(
                    category_id=uuid.UUID(category_id),
                    template_id=uuid.UUID(assignment["templateId"]),
                    discipline_id=uuid.UUID(discipline_id),
                )
            )
        default = slots.get(None)
        if default is not None:
            targets.append(
                NominationTarget(
                    category_id=uuid.UUID(category_id),
                    template_id=uuid.UUID(default["templateId"]),
                    excluded_discipline_ids=tuple(uuid.UUID(key) for key in overrides),
                )
            )
    return targets


def printable_targets(competition_id: uuid.UUID, category_ids: list[str]) -> list[NominationTarget]:
    """The resolved targets a run can actually print, never an empty list.

    Drops the targets whose template is gone or has no PDF behind it, and raises
    :class:`PrintTemplateNotReadyError` only when that leaves nothing. A genre is
    several targets now that a nomination may print on a template of its own, and
    failing a festival's whole package because one nomination's sheet is unfinished
    would hold the ready ones hostage to it — the summary reports per genre what is
    not ready, so the gap is visible before the run rather than inferred after it.

    Used by both the request that enqueues a job and the worker that runs it, so
    the two cannot disagree about what the run covers.
    """
    targets = [
        target
        for target in resolve_targets(competition_id, category_ids)
        if TemplateModel.objects.filter(id=target.template_id, deleted_at__isnull=True).exists()
        and TemplateDocumentModel.objects.filter(template__id=target.template_id, deleted_at__isnull=True).exists()
    ]
    if not targets:
        raise PrintTemplateNotReadyError("Нет ни одного жанра с назначенным шаблоном и загруженным PDF.")
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
    """Per-genre stats for **every** document type, one slot each.

    A genre assigns a template per type, so readiness is per type too: «Вокал» may
    be ready to print diplomas and have no thank-you template at all. One merged
    flag cannot say that, and reporting one is what let the generation page offer
    genres for a kind they had no template for.

    Each slot's forecast follows its own policy. A diploma is issued per
    performance, a thank-you letter per named teacher, an individual diploma per named
    member of a collective — three different denominators over the same entries. A
    per-teacher kind also reports the entries it cannot address at all.

    Counting happens **per nomination inside the genre**, because a nomination may
    print on a template of its own: an entry is forecast only when the template it
    would actually print on exists and has a PDF, and counted as ``withoutTemplate``
    when it does not. A genre-wide count could not tell the two apart, and would
    promise diplomas for nominations no run would produce.
    """
    assignments = {document_type: _assignments_by_category(competition_id, document_type) for document_type in DocumentType}
    # A slot is only "ready" to generate when its template also has a PDF.
    assigned_template_ids = {item["templateId"] for genre in assignments.values() for slots in genre.values() for item in slots.values()}
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
    discipline_names = {
        str(row["id"]): str(row["name"])
        for row in DisciplineModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).values("id", "name")
    }

    from apps.applications.infrastructure.models.submission import SubmissionModel

    category_of: dict[str, str] = {}
    # Keyed by (genre, nomination) — the pair that decides which template an entry
    # prints on. The empty string stands for "names no nomination".
    submissions: Counter[tuple[str, str]] = Counter()
    recipients: Counter[tuple[str, str]] = Counter()
    unaddressable: Counter[tuple[str, str]] = Counter()
    members: Counter[tuple[str, str]] = Counter()
    # The same narrowing the generation pipeline applies, so «Выступлений» is the
    # number a run will actually walk rather than every entry ever filed.
    for row in SubmissionModel.objects.filter(
        competition_id=competition_id,
        deleted_at__isnull=True,
        status__in=COMPETING_SUBMISSION_STATUSES,
    ).values("id", "performance", "teachers", "participants"):
        performance = row["performance"] or {}
        category_id = str(performance.get("nomination_id") or "")
        if not category_id:
            continue
        bucket = (category_id, str(performance.get("discipline_id") or ""))
        category_of[str(row["id"])] = category_id
        submissions[bucket] += 1
        named = _named_teachers(row["teachers"])
        recipients[bucket] += named
        if not named:
            unaddressable[bucket] += 1
        members[bucket] += _named_members(row["participants"])

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

    def buckets_of(category_id: str) -> list[str]:
        """Every nomination of this genre that has entries, plus the genre's own rows."""
        return sorted({discipline_id for (genre, discipline_id) in submissions if genre == category_id})

    def slot(document_type: DocumentType, category_id: str) -> dict[str, Any]:
        slots = assignments[document_type].get(category_id, {})
        default = slots.get(None)
        policy = policy_for(document_type)
        per_teacher = policy.per_teacher

        def denominator(bucket: tuple[str, str]) -> int:
            if per_teacher:
                return recipients[bucket]
            if policy.per_member:
                # One per person the applicants named, not one per entry: an ensemble
                # that named nobody contributes nothing to this slot.
                return members[bucket]
            return submissions[bucket]

        total = 0
        without_template = 0
        for discipline_id in buckets_of(category_id):
            bucket = (category_id, discipline_id)
            assignment = _resolve_slot(slots, discipline_id or None)
            if assignment is not None and assignment["templateId"] in templates_with_pdf:
                total += denominator(bucket)
            else:
                # Nothing to print these on — no template, or one with no PDF behind
                # it. Reported rather than folded into the forecast, so the number
                # beside the button is what a run will actually produce.
                without_template += denominator(bucket)

        ready = any(item["templateId"] in templates_with_pdf for item in slots.values())
        done = existing[document_type][category_id]
        return {
            "templateId": default["templateId"] if default else None,
            "templateName": default["templateName"] if default else None,
            # Assigned but with no uploaded PDF yet — cannot generate.
            "ready": ready,
            "existing": done,
            "willCreate": max(0, total - done) if ready else 0,
            # Entries a per-teacher kind cannot address; always 0 for the rest.
            "withoutRecipient": sum(unaddressable[(category_id, discipline_id)] for discipline_id in buckets_of(category_id)) if per_teacher else 0,
            # Entries whose nomination resolves to no printable template.
            "withoutTemplate": without_template,
            # The nominations that print on something other than the genre's default.
            "disciplines": [
                {
                    "disciplineId": discipline_id,
                    "discipline": discipline_names.get(str(discipline_id)),
                    "templateId": item["templateId"],
                    "templateName": item["templateName"],
                    "ready": item["templateId"] in templates_with_pdf,
                }
                for discipline_id, item in sorted(
                    ((key, value) for key, value in slots.items() if key is not None),
                    key=lambda pair: (discipline_names.get(str(pair[0])) or "").lower(),
                )
            ],
        }

    # A genre is listed when it has entries or a template of any kind at any level.
    listed = {category_id for (category_id, _) in submissions}
    for genre in assignments.values():
        listed |= set(genre)

    nominations: list[dict[str, Any]] = [
        {
            "categoryId": category_id,
            "nomination": category_names.get(category_id),
            "submissions": sum(submissions[(category_id, discipline_id)] for discipline_id in buckets_of(category_id)),
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
    """Create + enqueue a print-package job for the chosen genres (or all).

    ``force`` re-renders print PDFs for diplomas that already have one.

    Targets whose template is gone or has no PDF are **dropped**, and the run goes
    ahead with the rest; only a selection where nothing is printable is refused.
    That is a change the second level of assignment forces: a genre is now several
    targets, and failing the whole festival's package because one nomination's own
    sheet has no PDF yet would make the print run hostage to the least finished
    layout in it. The summary says per genre what is and is not ready, so the
    organizer is not learning it from a silent gap.

    The actor is recorded on the job because only the request knows who asked; the
    worker carries it into the generation archive once the run completes.
    """
    # Resolved here only to refuse an impossible run up front; the worker resolves
    # again when it starts, so a template uploaded in between is picked up.
    printable_targets(competition_id, category_ids)

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
