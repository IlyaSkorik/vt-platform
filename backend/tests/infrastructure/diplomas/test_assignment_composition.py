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
    return TemplateModel.objects.create(type="DIPLOMA", name=name)


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


def test_one_template_assigned_to_several_nominations_at_once() -> None:
    template = _template()
    competition_id = str(uuid.uuid4())
    nominations = [str(uuid.uuid4()) for _ in range(3)]

    created = composition.create_assignments(
        competition_id=competition_id,
        category_ids=nominations,
        template_id=str(template.id),
    )

    # Returned in the order asked for, so the caller can match them up.
    assert [item["categoryId"] for item in created] == nominations
    assert {item["templateId"] for item in created} == {str(template.id)}
    assert len(composition.list_assignments()) == 3


def test_a_nomination_named_twice_is_assigned_once() -> None:
    template = _template()
    category_id = str(uuid.uuid4())

    created = composition.create_assignments(
        competition_id=str(uuid.uuid4()),
        category_ids=[category_id, category_id],
        template_id=str(template.id),
    )

    assert len(created) == 1
    assert len(composition.list_assignments()) == 1


def test_a_batch_with_one_taken_nomination_creates_nothing() -> None:
    """All or nothing: a half-applied batch is invisible in the table."""
    template = _template()
    competition_id = str(uuid.uuid4())
    taken = str(uuid.uuid4())
    free = str(uuid.uuid4())
    composition.create_assignment(competition_id=competition_id, category_id=taken, template_id=str(template.id))

    with pytest.raises(AssignmentConflictError):
        composition.create_assignments(
            competition_id=competition_id,
            category_ids=[free, taken],
            template_id=str(template.id),
        )

    # Only the original assignment survives — `free` was rolled back with the batch.
    assert [item["categoryId"] for item in composition.list_assignments()] == [taken]


def test_a_batch_only_fills_the_templates_own_slot() -> None:
    """A thank-you batch leaves the same nominations' diploma slots alone."""
    diploma = _template()
    thanks = TemplateModel.objects.create(type="THANK_YOU", name="Благодарность")
    competition_id = str(uuid.uuid4())
    nominations = [str(uuid.uuid4()) for _ in range(2)]
    composition.create_assignments(competition_id=competition_id, category_ids=nominations, template_id=str(diploma.id))

    composition.create_assignments(competition_id=competition_id, category_ids=nominations, template_id=str(thanks.id))

    by_type: dict[str, set[str]] = {}
    for item in composition.list_assignments():
        by_type.setdefault(str(item["documentType"]), set()).add(str(item["categoryId"]))
    assert by_type == {"DIPLOMA": set(nominations), "THANK_YOU": set(nominations)}


def _field(page: int = 1, x: float = 0.1, y: float = 0.2) -> dict[str, object]:
    return {"page": page, "type": "participant_name", "x": x, "y": y, "width": 0.4, "height": 0.08}


def test_layout_starts_empty_with_revision() -> None:
    template = _template()
    layout = composition.get_template_layout(str(template.id))
    assert layout["fields"] == []
    assert layout["revision"] == template.version


def test_replace_layout_persists_and_bumps_revision() -> None:
    template = _template()
    before = composition.get_template_layout(str(template.id))["revision"]

    saved = composition.replace_template_layout(template_id=str(template.id), fields=[_field(x=0.1), _field(x=0.5)])

    assert len(saved["fields"]) == 2
    assert saved["revision"] == before + 1
    assert saved["fields"][0]["type"] == "participant_name"
    # Reloading returns the same layout.
    assert composition.get_template_layout(str(template.id))["fields"][0]["x"] == 0.1


def test_replace_layout_is_a_full_replace() -> None:
    template = _template()
    composition.replace_template_layout(template_id=str(template.id), fields=[_field(), _field(), _field()])
    composition.replace_template_layout(template_id=str(template.id), fields=[_field(x=0.9)])

    layout = composition.get_template_layout(str(template.id))
    assert len(layout["fields"]) == 1
    assert layout["fields"][0]["x"] == 0.9


def test_layout_persists_field_style() -> None:
    template = _template()
    style = {"fontFamily": "Montserrat", "fontSize": 36, "textAlign": "left", "color": "#ff0000"}
    field = {**_field(), "style": style}

    composition.replace_template_layout(template_id=str(template.id), fields=[field])

    saved = composition.get_template_layout(str(template.id))["fields"][0]
    assert saved["style"]["fontSize"] == 36
    assert saved["style"]["textAlign"] == "left"
    assert saved["style"]["color"] == "#ff0000"


def test_layout_persists_nomination_block_config() -> None:
    template = _template()
    field = {
        **_field(),
        "type": "nomination_block",
        "binding": "nomination.block",
        "config": {"parts": ["title", "age_category"], "prefix": "Номинация:"},
    }

    composition.replace_template_layout(template_id=str(template.id), fields=[field])

    saved = composition.get_template_layout(str(template.id))["fields"][0]
    assert saved["type"] == "nomination_block"
    assert saved["config"]["parts"] == ["title", "age_category"]
    assert saved["config"]["prefix"] == "Номинация:"


def test_layout_simple_field_has_empty_config() -> None:
    template = _template()

    composition.replace_template_layout(template_id=str(template.id), fields=[_field()])

    saved = composition.get_template_layout(str(template.id))["fields"][0]
    assert saved["config"] == {}


def test_layout_persists_field_binding() -> None:
    template = _template()
    field = {**_field(), "binding": "participant.display_name"}

    composition.replace_template_layout(template_id=str(template.id), fields=[field])

    saved = composition.get_template_layout(str(template.id))["fields"][0]
    assert saved["binding"] == "participant.display_name"


def test_layout_persists_free_text_value() -> None:
    template = _template()
    field = {
        "page": 1,
        "type": "free_text",
        "binding": "",
        "value": "Диплом I степени",
        "x": 0.1,
        "y": 0.1,
        "width": 0.4,
        "height": 0.08,
    }

    composition.replace_template_layout(template_id=str(template.id), fields=[field])

    saved = composition.get_template_layout(str(template.id))["fields"][0]
    assert saved["type"] == "free_text"
    assert saved["binding"] == ""
    assert saved["value"] == "Диплом I степени"


def test_layout_unknown_template_raises() -> None:
    with pytest.raises(TemplateNotFoundError):
        composition.get_template_layout(str(uuid.uuid4()))
    with pytest.raises(TemplateNotFoundError):
        composition.replace_template_layout(template_id=str(uuid.uuid4()), fields=[_field()])


def test_set_template_document_attaches_and_replaces() -> None:
    template = _template()
    assert composition.list_templates()[0]["document"] is None

    first = composition.set_template_document(
        template_id=str(template.id),
        file_reference="/media/diplomas/templates/x/a.pdf",
        original_filename="a.pdf",
    )
    listed = composition.list_templates()[0]
    assert listed["document"]["id"] == first["id"]
    assert listed["document"]["fileReference"] == "/media/diplomas/templates/x/a.pdf"

    # Replacing the PDF makes the newest upload the current one.
    second = composition.set_template_document(
        template_id=str(template.id),
        file_reference="/media/diplomas/templates/x/b.pdf",
        original_filename="b.pdf",
    )
    current = composition.list_templates()[0]["document"]
    assert current["id"] == second["id"]
    assert current["fileReference"] == "/media/diplomas/templates/x/b.pdf"


def test_set_document_unknown_template_raises() -> None:
    with pytest.raises(TemplateNotFoundError):
        composition.set_template_document(
            template_id=str(uuid.uuid4()),
            file_reference="/media/x.pdf",
        )


def test_create_template_starts_empty_library() -> None:
    assert composition.list_templates() == []

    created = composition.create_template(name="Диплом заочный", document_type="DIPLOMA", description="")

    assert created["name"] == "Диплом заочный"
    assert created["type"] == "DIPLOMA"
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
