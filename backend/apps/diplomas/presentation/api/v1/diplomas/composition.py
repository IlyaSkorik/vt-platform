"""Read/write helpers for the Diplomas workspace REST surface.

Keeps the views thin: each function reads or mutates the Diplomas persistence
models and resolves the cross-context labels (competition title, nomination name)
the organizer UI needs. Cross-context reads go straight to the Competitions ORM
by id (id-only references, ARCH-001 §7.2) — Diplomas never owns those rows.
"""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError
from django.db.models import Count, Q
from django.utils import timezone

from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.domain.exceptions import (
    AssignmentConflictError,
    AssignmentNotFoundError,
    TemplateNotFoundError,
)
from apps.diplomas.infrastructure.models import AssignmentModel, TemplateModel

__all__ = [
    "create_assignment",
    "create_template",
    "delete_assignment",
    "list_assignments",
    "list_templates",
]

def _template_json(row: TemplateModel, usage: int) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "usageCount": usage,
        "updatedAt": row.updated_at,
    }


def list_templates() -> list[dict[str, Any]]:
    """Every template in the library, with how many assignments use each one."""
    rows = (
        TemplateModel.objects.filter(deleted_at__isnull=True)
        .annotate(usage=Count("assignments", filter=Q(assignments__deleted_at__isnull=True)))
        .order_by("name")
    )
    return [_template_json(row, row.usage) for row in rows]


def create_template(*, name: str, description: str = "") -> dict[str, Any]:
    """Add a new, self-contained template to the library (created by the organizer)."""
    row = TemplateModel.objects.create(name=name.strip(), description=description.strip())
    return _template_json(row, 0)


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
