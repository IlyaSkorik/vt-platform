"""Integration tests for the Diplomas assignment composition helpers.

Real Django ORM against real PostgreSQL (ARCH-001 §28.2), as for every
``tests/infrastructure`` suite. Covers the assignment lifecycle (create → list →
delete), the uniqueness conflict on (competition, nomination), the not-found
paths, and the template usage-count projection.
"""

from __future__ import annotations

import uuid

import pytest

from apps.diplomas.domain.exceptions import (
    AssignmentConflictError,
    AssignmentNotFoundError,
    TemplateNotFoundError,
)
from apps.diplomas.infrastructure.models import TemplateModel
from apps.diplomas.presentation.api.v1.diplomas import composition

pytestmark = pytest.mark.django_db


def _template(name: str = "Диплом очный") -> TemplateModel:
    return TemplateModel.objects.create(name=name)


def test_create_and_list_assignment() -> None:
    template = _template()
    competition_id = str(uuid.uuid4())
    category_id = str(uuid.uuid4())

    created = composition.create_assignment(
        competition_id=competition_id,
        category_id=category_id,
        template_id=str(template.id),
    )

    assert created["competitionId"] == competition_id
    assert created["categoryId"] == category_id
    assert created["templateId"] == str(template.id)

    listed = composition.list_assignments()
    assert [item["id"] for item in listed] == [created["id"]]


def test_duplicate_nomination_raises_conflict() -> None:
    template = _template()
    competition_id = str(uuid.uuid4())
    category_id = str(uuid.uuid4())
    composition.create_assignment(
        competition_id=competition_id,
        category_id=category_id,
        template_id=str(template.id),
    )

    with pytest.raises(AssignmentConflictError):
        composition.create_assignment(
            competition_id=competition_id,
            category_id=category_id,
            template_id=str(template.id),
        )


def test_unknown_template_raises_not_found() -> None:
    with pytest.raises(TemplateNotFoundError):
        composition.create_assignment(
            competition_id=str(uuid.uuid4()),
            category_id=str(uuid.uuid4()),
            template_id=str(uuid.uuid4()),
        )


def test_delete_assignment_then_missing() -> None:
    template = _template()
    created = composition.create_assignment(
        competition_id=str(uuid.uuid4()),
        category_id=str(uuid.uuid4()),
        template_id=str(template.id),
    )

    composition.delete_assignment(created["id"])
    assert composition.list_assignments() == []

    with pytest.raises(AssignmentNotFoundError):
        composition.delete_assignment(created["id"])


def test_deleting_frees_the_nomination_for_reuse() -> None:
    template = _template()
    competition_id = str(uuid.uuid4())
    category_id = str(uuid.uuid4())
    first = composition.create_assignment(
        competition_id=competition_id,
        category_id=category_id,
        template_id=str(template.id),
    )
    composition.delete_assignment(first["id"])

    # The partial unique constraint excludes soft-deleted rows, so the same
    # (competition, nomination) pair can be assigned again.
    second = composition.create_assignment(
        competition_id=competition_id,
        category_id=category_id,
        template_id=str(template.id),
    )
    assert second["id"] != first["id"]


def test_create_template_starts_empty_library() -> None:
    assert composition.list_templates() == []

    created = composition.create_template(name="Диплом заочный", description="")

    assert created["name"] == "Диплом заочный"
    assert created["usageCount"] == 0
    assert [item["id"] for item in composition.list_templates()] == [created["id"]]


def test_template_usage_count() -> None:
    template = _template()
    assert composition.list_templates()[0]["usageCount"] == 0

    composition.create_assignment(
        competition_id=str(uuid.uuid4()),
        category_id=str(uuid.uuid4()),
        template_id=str(template.id),
    )

    by_id = {item["id"]: item for item in composition.list_templates()}
    assert by_id[str(template.id)]["usageCount"] == 1
