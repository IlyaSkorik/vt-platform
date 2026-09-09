"""Read/write helpers for the Diplomas workspace REST surface.

Keeps the views thin: each function reads or mutates the Diplomas persistence
models and resolves the cross-context labels (competition title, nomination name)
the organizer UI needs. Cross-context reads go straight to the Competitions ORM
by id (id-only references, ARCH-001 §7.2) — Diplomas never owns those rows.

**Where the organization boundary is enforced, and where it is not.** The listing
functions take a :class:`~apps.diplomas.presentation.scope.Scope` and narrow
themselves — a list is the one place an unscoped query silently returns another
organization's rows, so the narrowing belongs with the query. Reaching a single
template or competition *by id* is refused earlier, in the view, so the answer is a
403 that says why rather than a 404 that pretends the row is absent; that mirrors
``CompetitionViewSet.initial``. Functions here that take an id therefore assume the
view has already decided the caller may touch it.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.domain.document_types import DocumentType, policy_for
from apps.diplomas.domain.exceptions import (
    AssignmentConflictError,
    AssignmentNotFoundError,
    FieldTypeNotAllowedError,
    TemplateNotFoundError,
)
from apps.diplomas.infrastructure.models import (
    AssignmentModel,
    TemplateDocumentModel,
    TemplateFieldModel,
    TemplateModel,
)
from apps.diplomas.presentation.scope import Scope

__all__ = [
    "create_assignment",
    "create_assignments",
    "create_template",
    "delete_assignment",
    "get_template_layout",
    "list_assignments",
    "list_assignments_by_ids",
    "list_templates",
    "replace_template_layout",
    "set_template_document",
]


def _document_json(row: TemplateDocumentModel) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "fileReference": row.file_reference,
        "originalFilename": row.original_filename,
        "pageCount": row.page_count,
        "uploadedAt": row.created_at,
    }


def _template_json(row: TemplateModel, usage: int, document: TemplateDocumentModel | None) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "type": row.type,
        "usageCount": usage,
        "document": _document_json(document) if document is not None else None,
        "updatedAt": row.updated_at,
    }


def _current_documents_by_template(template_ids: list[str]) -> dict[str, TemplateDocumentModel]:
    """The latest non-deleted document for each template (most recent wins)."""
    current: dict[str, TemplateDocumentModel] = {}
    rows = TemplateDocumentModel.objects.filter(template__id__in=template_ids, deleted_at__isnull=True).order_by("template_id", "-created_at")
    for row in rows:
        key = str(row.template_id)
        if key not in current:
            current[key] = row
    return current


def list_templates(*, scope: Scope, document_type: str | None = None) -> list[dict[str, Any]]:
    """The caller's own template library, with usage count and current PDF (if any).

    Narrowed to one kind when ``document_type`` is given — which is how a
    nomination's thank-you slot offers only ``THANK_YOU`` templates.

    ``scope`` has no default on purpose. Every caller has to state whose library it
    is asking for, so forgetting to scope is a ``TypeError`` at import time rather
    than a listing that quietly spans the platform.
    """
    query = scope.apply(TemplateModel.objects.filter(deleted_at__isnull=True))
    if document_type:
        query = query.filter(type=document_type)
    rows = list(query.annotate(usage=Count("assignments", filter=Q(assignments__deleted_at__isnull=True))).order_by("type", "name"))
    documents = _current_documents_by_template([str(row.id) for row in rows])
    return [_template_json(row, row.usage, documents.get(str(row.id))) for row in rows]


def create_template(*, organizer_id: uuid.UUID, name: str, document_type: str, description: str = "") -> dict[str, Any]:
    """Add a new, self-contained template to one organization's library.

    ``document_type`` is required: a layout is authored for one kind of document,
    so a template with no declared kind could not be safely rendered as anything.

    ``organizer_id`` is a concrete id rather than a :class:`Scope`, because creating
    is the one operation with no sensible answer for the two non-organization
    scopes: "every organization" does not name an owner and "none" has none. The
    view turns both into a refusal before reaching here.
    """
    row = TemplateModel.objects.create(
        organizer_id=organizer_id,
        name=name.strip(),
        description=description.strip(),
        type=document_type,
    )
    return _template_json(row, 0, None)


def _field_json(row: TemplateFieldModel) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "templateId": str(row.template_id),
        "page": row.page,
        "type": row.type,
        "binding": row.binding,
        "value": row.value,
        "x": row.x,
        "y": row.y,
        "width": row.width,
        "height": row.height,
        "rotation": row.rotation,
        "sortOrder": row.sort_order,
        "style": row.style or {},
        "config": row.config or {},
        "createdAt": row.created_at,
        "updatedAt": row.updated_at,
    }


def _template_revision(template_id: str) -> int:
    row = TemplateModel.objects.filter(id=template_id).values("version").first()
    return int(row["version"]) if row else 0


def get_template_layout(template_id: str) -> dict[str, Any]:
    """The template's saved fields plus its layout revision.

    Raises :class:`TemplateNotFoundError` for an unknown template.
    """
    if not TemplateModel.objects.filter(id=template_id, deleted_at__isnull=True).exists():
        raise TemplateNotFoundError("Шаблон не найден.")
    rows = TemplateFieldModel.objects.filter(template__id=template_id, deleted_at__isnull=True).order_by("page", "sort_order", "created_at")
    return {"fields": [_field_json(row) for row in rows], "revision": _template_revision(template_id)}


def replace_template_layout(*, template_id: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Atomically replace the whole layout with `fields` and bump the revision.

    The entire layout is saved as one document (not per-field requests): the prior
    fields are removed and the new set inserted in a single transaction, so a save
    is all-or-nothing. Returns the persisted fields (with ids) and the new
    revision. Raises :class:`TemplateNotFoundError` for an unknown template.
    """
    with transaction.atomic():
        template = TemplateModel.objects.select_for_update().filter(id=template_id, deleted_at__isnull=True).first()
        if template is None:
            raise TemplateNotFoundError("Шаблон не найден.")

        # A layout may only carry what its kind of document can print. The editor
        # hides the rest, so this catches a stale client or a hand-made request —
        # and keeps a thank-you template from ever holding a degree or a QR block.
        policy = policy_for(DocumentType(template.type))
        rejected = sorted({str(field.get("type") or "") for field in fields if not policy.allows_field(str(field.get("type") or ""))})
        if rejected:
            raise FieldTypeNotAllowedError(f"Документ типа «{template.type}» не может содержать поля: {', '.join(rejected)}.")

        # Hard-delete the previous layout: fields have no history of their own yet
        # (versioning lives on the template revision), so a clean replace is correct.
        TemplateFieldModel.objects.filter(template__id=template_id).delete()
        rows = [
            TemplateFieldModel(
                template_id=template_id,
                page=int(field["page"]),
                type=str(field["type"]),
                binding=str(field.get("binding") or ""),
                value=str(field.get("value") or ""),
                x=float(field["x"]),
                y=float(field["y"]),
                width=float(field["width"]),
                height=float(field["height"]),
                rotation=float(field.get("rotation", 0) or 0),
                # z-order follows array order; the request's sortOrder is advisory.
                sort_order=index,
                style=dict(field.get("style") or {}),
                config=dict(field.get("config") or {}),
            )
            for index, field in enumerate(fields)
        ]
        TemplateFieldModel.objects.bulk_create(rows)

        template.version = F("version") + 1
        template.updated_at = timezone.now()
        template.save(update_fields=["version", "updated_at"])

    return get_template_layout(template_id)


def set_template_document(*, template_id: str, file_reference: str, original_filename: str = "", page_count: int = 0) -> dict[str, Any]:
    """Attach (or replace) the template's backing PDF.

    Soft-deletes any current document so the newest upload becomes the current
    one, then returns the new document. Raises :class:`TemplateNotFoundError` for
    an unknown template.
    """
    if not TemplateModel.objects.filter(id=template_id, deleted_at__isnull=True).exists():
        raise TemplateNotFoundError("Шаблон не найден.")
    now = timezone.now()
    TemplateDocumentModel.objects.filter(template__id=template_id, deleted_at__isnull=True).update(deleted_at=now, updated_at=now)
    row = TemplateDocumentModel.objects.create(
        template_id=template_id,
        file_reference=file_reference,
        original_filename=original_filename,
        page_count=page_count,
    )
    return _document_json(row)


def list_assignments(*, scope: Scope) -> list[dict[str, Any]]:
    """The caller's own assignments, with competition/nomination/template labels.

    Narrowed on **both** sides of the binding, which is not belt-and-braces. An
    assignment names a template (owned in this context) and a competition (owned in
    Competitions), and the row resolves the competition's title and the nomination's
    name into its own JSON. Filtering by the template alone would still render a
    label belonging to whoever runs that competition — so a row is admitted only
    when the caller owns the template *and* runs the competition.
    """
    query = scope.apply(AssignmentModel.objects.filter(deleted_at__isnull=True), field="template__organizer_id")
    # Keyed off the id rather than off `everything`, which gets all three scopes right
    # for one condition: the operator and the empty scope both have no id, and the
    # empty one was already reduced to `.none()` by `apply` above.
    #
    # A second condition rather than a join: `competition_id` is an id-only reference
    # with no FK to follow (ARCH-001 §7.2).
    if (organization_id := scope.organization_id) is not None:
        query = query.filter(
            competition_id__in=CompetitionModel.objects.filter(
                organizer_id=organization_id,
                deleted_at__isnull=True,
            ).values("id")
        )
    rows = list(query.select_related("template").order_by("-created_at"))
    competition_ids = {row.competition_id for row in rows}
    category_ids = {row.category_id for row in rows}
    competition_title = {
        str(item["id"]): str(item["title"]) for item in CompetitionModel.objects.filter(id__in=competition_ids).values("id", "title")
    }
    category_name = {str(item["id"]): str(item["name"]) for item in CategoryModel.objects.filter(id__in=category_ids).values("id", "name")}
    return [
        {
            "id": str(row.id),
            "competitionId": str(row.competition_id),
            "competition": competition_title.get(str(row.competition_id)),
            "categoryId": str(row.category_id),
            "nomination": category_name.get(str(row.category_id)),
            "templateId": str(row.template_id),
            "templateName": row.template.name,
            "documentType": row.document_type,
            "createdAt": row.created_at,
            "updatedAt": row.updated_at,
        }
        for row in rows
    ]


def create_assignment(*, competition_id: str, category_id: str, template_id: str, scope: Scope) -> dict[str, Any]:
    """Bind a template to one document slot of a (competition, nomination) pair.

    A batch of one: see :func:`create_assignments` for the slot derivation and the
    errors raised.
    """
    return create_assignments(competition_id=competition_id, category_ids=[category_id], template_id=template_id, scope=scope)[0]


def create_assignments(*, competition_id: str, category_ids: list[str], template_id: str, scope: Scope) -> list[dict[str, Any]]:
    """Bind one template to the same slot of several nominations at once.

    The organizer's real unit of work: a competition's nominations usually share a
    diploma design, and assigning it one at a time is the same decision repeated.

    Which slot the batch fills is **derived from the template's own type** rather
    than passed in: a ``THANK_YOU`` template can only ever be a nomination's
    thank-you template. That makes a slot/template mismatch unrepresentable here, so
    a batch fills one slot across the nominations and leaves the other untouched.

    All or nothing. A batch that leaves some nominations assigned and others not is
    worse than one that fails outright, because the table does not say which half
    went through. Duplicate ids in one request are collapsed rather than rejected —
    naming a nomination twice means what naming it once means.

    Raises :class:`TemplateNotFound` for an unknown template and
    :class:`AssignmentConflict` for the first nomination that already has a template
    of that kind — a diploma assignment therefore does not block a thank-you one.

    The template lookup is scoped even though the view has already refused a
    cross-organization template with a 403. Not redundancy for its own sake: this is
    the write that *creates* the link between a template and a competition, so it is
    the one place where a missed check would persist a crossing rather than merely
    display one. A wrong answer here outlives the request.
    """
    template = scope.apply(TemplateModel.objects.filter(id=template_id, deleted_at__isnull=True)).only("type").first()
    if template is None:
        raise TemplateNotFoundError("Шаблон не найден.")
    document_type = template.type
    wanted = list(dict.fromkeys(category_ids))

    with transaction.atomic():
        taken = set(
            AssignmentModel.objects.filter(
                competition_id=competition_id,
                category_id__in=wanted,
                document_type=document_type,
                deleted_at__isnull=True,
            ).values_list("category_id", flat=True)
        )
        if taken:
            raise AssignmentConflictError("Для этой номинации уже назначен шаблон такого типа.")
        try:
            rows = AssignmentModel.objects.bulk_create(
                [
                    AssignmentModel(
                        competition_id=competition_id,
                        category_id=category_id,
                        template_id=template_id,
                        document_type=document_type,
                    )
                    for category_id in wanted
                ]
            )
        except IntegrityError as exc:  # pragma: no cover - unique race
            raise AssignmentConflictError("Для этой номинации уже назначен шаблон такого типа.") from exc
    return list_assignments_by_ids([str(row.id) for row in rows], scope=scope)


def list_assignments_by_ids(assignment_ids: list[str], *, scope: Scope) -> list[dict[str, Any]]:
    """Return these assignments' JSON, in the order asked for (used after a create).

    One listing pass for the whole batch: the label resolution behind
    :func:`list_assignments` is the same work whether one row or twenty came back.
    Reading through the scoped listing is also what keeps an id from another
    organization from being renderable here — it simply is not in the dictionary,
    and the lookup below raises.
    """
    by_id = {item["id"]: item for item in list_assignments(scope=scope)}
    try:
        return [by_id[assignment_id] for assignment_id in assignment_ids]
    except KeyError as exc:
        raise AssignmentNotFoundError("Назначение шаблона не найдено.") from exc


def list_assignments_by_id(assignment_id: str, *, scope: Scope) -> dict[str, Any]:
    """Return a single assignment's JSON (used right after a create)."""
    return list_assignments_by_ids([assignment_id], scope=scope)[0]


def delete_assignment(assignment_id: str, *, scope: Scope) -> None:
    """Soft-delete one of the caller's own assignments.

    Raises :class:`AssignmentNotFound` when the id is unknown **or** belongs to
    another organization, and the two are deliberately the same answer. Unlike a
    template or a competition id — which a client legitimately holds and passes
    around, and for which a 403 explaining the refusal is the better answer — an
    assignment id is an internal handle the client only ever receives from a scoped
    listing. "Not in your list" is therefore the honest response, and it says
    nothing about what exists elsewhere.
    """
    row = scope.apply(
        AssignmentModel.objects.filter(id=assignment_id, deleted_at__isnull=True),
        field="template__organizer_id",
    ).first()
    if row is None:
        raise AssignmentNotFoundError("Назначение шаблона не найдено.")
    now = timezone.now()
    row.deleted_at = now
    row.updated_at = now
    row.version += 1
    row.save(update_fields=["deleted_at", "updated_at", "version"])
