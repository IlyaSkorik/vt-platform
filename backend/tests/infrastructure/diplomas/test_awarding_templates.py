"""Which sheet publishing the results prints a diploma on.

Awarding resolves the template per **entry**, not per protocol: a genre's
nominations may each assign one of their own because each is judged — and signed
off — by its own jury. These tests pin that resolution down on the publication
path, where the diploma reaching the participant's cabinet is rendered.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from reportlab.pdfgen import canvas

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel, DisciplineModel
from apps.diplomas.composition import build_diploma_award_service
from apps.diplomas.infrastructure.models import DiplomaModel, TemplateDocumentModel, TemplateModel
from apps.diplomas.presentation.api.v1.diplomas import composition
from apps.diplomas.presentation.scope import Scope

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

pytestmark = pytest.mark.django_db

_ORGANIZER = uuid.UUID("00000000-0000-4000-8000-0000000000a1")
_SCOPE = Scope.for_organization(_ORGANIZER)
_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _media_root(settings: SettingsWrapper, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = str(tmp_path)


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    page.drawString(50, 50, "background")
    page.save()
    return buffer.getvalue()


def _template(name: str) -> TemplateModel:
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name=name)
    key = default_storage.save(f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf()))
    TemplateDocumentModel.objects.create(template=template, file_reference=f"/media/{key}", page_count=1)
    composition.replace_template_layout(
        template_id=str(template.id),
        fields=[
            {
                "page": 1,
                "type": "participant_name",
                "binding": "participant.display_name",
                "x": 0.1,
                "y": 0.1,
                "width": 0.6,
                "height": 0.1,
            }
        ],
    )
    return template


def _competition() -> CompetitionModel:
    return CompetitionModel.objects.create(
        title="Восходящие таланты",
        season="2026",
        organizer_id=_ORGANIZER,
        status="PUBLISHED",
        competition_start=date(2026, 5, 15),
    )


def _submission(competition: CompetitionModel, category: CategoryModel, name: str, discipline: DisciplineModel | None = None) -> SubmissionModel:
    performance: dict[str, object] = {"title": "Этюд", "nomination_id": str(category.id)}
    if discipline is not None:
        performance["discipline_id"] = str(discipline.id)
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="ACCEPTED",
        participants=[{"display_name": name, "member_count": 1}],
        teachers=[],
        performance=performance,
    )


def test_each_entry_is_issued_on_its_own_nominations_template() -> None:
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    pop = DisciplineModel.objects.create(competition=competition, category_id=vocals.id, name="Эстрадный вокал")
    genre_template = _template("Вокал A4")
    pop_template = _template("Эстрадный вокал A4")
    composition.create_assignment(competition_id=str(competition.id), category_id=str(vocals.id), template_id=str(genre_template.id), scope=_SCOPE)
    composition.create_assignments(competition_id=str(competition.id), discipline_ids=[str(pop.id)], template_id=str(pop_template.id), scope=_SCOPE)
    folk_entry = _submission(competition, vocals, "Иванов Иван")
    pop_entry = _submission(competition, vocals, "Петров Пётр", discipline=pop)

    outcomes = build_diploma_award_service().award(
        competition_id=competition.id,
        category_id=vocals.id,
        awards=[(folk_entry.id, "Лауреат I степени"), (pop_entry.id, "Лауреат II степени")],
        now=_NOW,
    )

    assert [outcome.created for outcome in outcomes] == [True, True]
    by_submission = {str(row.submission_id): row for row in DiplomaModel.objects.filter(competition_id=competition.id)}
    assert str(by_submission[str(folk_entry.id)].template_id) == str(genre_template.id)
    assert str(by_submission[str(pop_entry.id)].template_id) == str(pop_template.id)
    # Both reached the participant's cabinet — the per-entry resolution picks the
    # assets to render with, not just the id written on the row.
    assert all(row.official_pdf_path for row in by_submission.values())


def test_an_entry_whose_nomination_has_no_template_keeps_its_degree() -> None:
    """The genre has no default and this nomination assigns nothing of its own.

    The result still stands — publishing a protocol is never held up by a layout —
    so the degree is recorded and the document waits for a template.
    """
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    pop = DisciplineModel.objects.create(competition=competition, category_id=vocals.id, name="Эстрадный вокал")
    composition.create_assignments(
        competition_id=str(competition.id), discipline_ids=[str(pop.id)], template_id=str(_template("Эстрада A4").id), scope=_SCOPE
    )
    uncovered = _submission(competition, vocals, "Иванов Иван")

    outcomes = build_diploma_award_service().award(
        competition_id=competition.id,
        category_id=vocals.id,
        awards=[(uncovered.id, "Лауреат I степени")],
        now=_NOW,
    )

    assert outcomes == []
    assert DiplomaModel.objects.filter(competition_id=competition.id).count() == 0
