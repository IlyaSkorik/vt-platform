"""Read/write helpers for the Diplomas workspace REST surface.

Keeps the views thin: each function reads or mutates the Diplomas persistence
models and resolves the cross-context labels (competition title, nomination name)
the organizer UI needs. Cross-context reads go straight to the Competitions ORM
by id (id-only references, ARCH-001 §7.2) — Diplomas never owns those rows.
"""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.domain.exceptions import (
    AssignmentConflictError,
    AssignmentNotFoundError,
    TemplateNotFoundError,
)
from apps.diplomas.infrastructure.models import (
    AssignmentModel,
    TemplateDocumentModel,
    TemplateFieldModel,
    TemplateModel,
)

__all__ = [
    "create_assignment",
    "create_template",
    "delete_assignment",
    "get_template_layout",
    "list_assignments",
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


def _template_json(
    row: TemplateModel, usage: int, document: TemplateDocumentModel | None
) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "usageCount": usage,
        "document": _document_json(document) if document is not None else None,
        "updatedAt": row.updated_at,
    }


def _current_documents_by_template(template_ids: list[str]) -> dict[str, TemplateDocumentModel]:
    """The latest non-deleted document for each template (most recent wins)."""
    current: dict[str, TemplateDocumentModel] = {}
    rows = TemplateDocumentModel.objects.filter(
        template__id__in=template_ids, deleted_at__isnull=True
    ).order_by("template_id", "-created_at")
    for row in rows:
        key = str(row.template_id)
        if key not in current:
            current[key] = row
    return current


def list_templates() -> list[dict[str, Any]]:
    """Every template in the library, with usage count and current PDF (if any)."""
    rows = list(
        TemplateModel.objects.filter(deleted_at__isnull=True)
        .annotate(usage=Count("assignments", filter=Q(assignments__deleted_at__isnull=True)))
        .order_by("name")
    )
    documents = _current_documents_by_template([str(row.id) for row in rows])
    return [_template_json(row, row.usage, documents.get(str(row.id))) for row in rows]


def create_template(*, name: str, description: str = "") -> dict[str, Any]:
    """Add a new, self-contained template to the library (created by the organizer)."""
    row = TemplateModel.objects.create(name=name.strip(), description=description.strip())
    return _template_json(row, 0, None)


def _field_json(row: TemplateFieldModel) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "templateId": str(row.template_id),
        "page": row.page,
        "type": row.type,
        "x": row.x,
        "y": row.y,
        "width": row.width,
        "height": row.height,
        "rotation": row.rotation,
        "sortOrder": row.sort_order,
        "style": row.style or {},
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
        raise TemplateNotFoundError("Template was not found.")
    rows = TemplateFieldModel.objects.filter(
        template__id=template_id, deleted_at__isnull=True
    ).order_by("page", "sort_order", "created_at")
    return {"fields": [_field_json(row) for row in rows], "revision": _template_revision(template_id)}


def replace_template_layout(*, template_id: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Atomically replace the whole layout with `fields` and bump the revision.

    The entire layout is saved as one document (not per-field requests): the prior
    fields are removed and the new set inserted in a single transaction, so a save
    is all-or-nothing. Returns the persisted fields (with ids) and the new
    revision. Raises :class:`TemplateNotFoundError` for an unknown template.
    """
    with transaction.atomic():
        template = (
            TemplateModel.objects.select_for_update()
            .filter(id=template_id, deleted_at__isnull=True)
            .first()
        )
        if template is None:
            raise TemplateNotFoundError("Template was not found.")

        # Hard-delete the previous layout: fields have no history of their own yet
        # (versioning lives on the template revision), so a clean replace is correct.
        TemplateFieldModel.objects.filter(template__id=template_id).delete()
        rows = [
            TemplateFieldModel(
                template_id=template_id,
                page=int(field["page"]),
                type=str(field["type"]),
                x=float(field["x"]),
                y=float(field["y"]),
                width=float(field["width"]),
                height=float(field["height"]),
                rotation=float(field.get("rotation", 0) or 0),
                # z-order follows array order; the request's sortOrder is advisory.
                sort_order=index,
                style=dict(field.get("style") or {}),
            )
            for index, field in enumerate(fields)
        ]
        TemplateFieldModel.objects.bulk_create(rows)

        template.version = F("version") + 1
        template.updated_at = timezone.now()
        template.save(update_fields=["version", "updated_at"])

    return get_template_layout(template_id)


def set_template_document(
    *, template_id: str, file_reference: str, original_filename: str = "", page_count: int = 0
) -> dict[str, Any]:
    """Attach (or replace) the template's backing PDF.

    Soft-deletes any current document so the newest upload becomes the current
    one, then returns the new document. Raises :class:`TemplateNotFoundError` for
    an unknown template.
    """
    if not TemplateModel.objects.filter(id=template_id, deleted_at__isnull=True).exists():
        raise TemplateNotFoundError("Template was not found.")
    now = timezone.now()
    TemplateDocumentModel.objects.filter(template__id=template_id, deleted_at__isnull=True).update(
        deleted_at=now, updated_at=now
    )
    row = TemplateDocumentModel.objects.create(
        template_id=template_id,
        file_reference=file_reference,
        original_filename=original_filename,
        page_count=page_count,
    )
    return _document_json(row)


def list_assignments() -> list[dict[str, Any]]:
    """Every assignment, with competition/nomination/template labels resolved."""
    rows = list(
        AssignmentModel.objects.filter(deleted_at__isnull=True)
        .select_related("template")
        .order_by("-created_at")
    )
    competition_ids = {row.competition_id for row in rows}
    category_ids = {row.category_id for row in rows}
    competition_title = {
        str(item["id"]): str(item["title"])
        for item in CompetitionModel.objects.filter(id__in=competition_ids).values("id", "title")
    }
    category_name = {
        str(item["id"]): str(item["name"])
        for item in CategoryModel.objects.filter(id__in=category_ids).values("id", "name")
    }
    return [
        {
            "id": str(row.id),
            "competitionId": str(row.competition_id),
            "competition": competition_title.get(str(row.competition_id)),
            "categoryId": str(row.category_id),
            "nomination": category_name.get(str(row.category_id)),
            "templateId": str(row.template_id),
            "templateName": row.template.name,
            "createdAt": row.created_at,
            "updatedAt": row.updated_at,
        }
        for row in rows
    ]


def create_assignment(*, competition_id: str, category_id: str, template_id: str) -> dict[str, Any]:
    """Bind a template to a (competition, nomination) pair.

    Raises :class:`TemplateNotFound` for an unknown template and
    :class:`AssignmentConflict` when the nomination is already assigned.
    """
    if not TemplateModel.objects.filter(id=template_id, deleted_at__isnull=True).exists():
        raise TemplateNotFoundError("Template was not found.")
    if AssignmentModel.objects.filter(
        competition_id=competition_id, category_id=category_id, deleted_at__isnull=True
    ).exists():
        raise AssignmentConflictError("This nomination already has a template assigned.")
    try:
        row = AssignmentModel.objects.create(
            competition_id=competition_id,
            category_id=category_id,
            template_id=template_id,
        )
    except IntegrityError as exc:  # pragma: no cover - unique race
        raise AssignmentConflictError("This nomination already has a template assigned.") from exc
    return list_assignments_by_id(str(row.id))


def list_assignments_by_id(assignment_id: str) -> dict[str, Any]:
    """Return a single assignment's JSON (used right after a create)."""
    for item in list_assignments():
        if item["id"] == assignment_id:
            return item
    raise AssignmentNotFoundError("Assignment was not found.")


def delete_assignment(assignment_id: str) -> None:
    """Soft-delete an assignment. Raises :class:`AssignmentNotFound` if unknown."""
    row = AssignmentModel.objects.filter(id=assignment_id, deleted_at__isnull=True).first()
    if row is None:
        raise AssignmentNotFoundError("Assignment was not found.")
    now = timezone.now()
    row.deleted_at = now
    row.updated_at = now
    row.version += 1
    row.save(update_fields=["deleted_at", "updated_at", "version"])
