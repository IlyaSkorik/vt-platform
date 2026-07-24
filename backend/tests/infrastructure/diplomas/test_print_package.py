"""Integration tests for mass print-package generation (per-nomination)."""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import UTC, date, datetime

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from reportlab.pdfgen import canvas

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.domain.exceptions import PrintTemplateNotReadyError
from apps.diplomas.domain.value_objects import DiplomaStatus
from apps.diplomas.infrastructure.models import DiplomaModel, TemplateDocumentModel, TemplateModel
from apps.diplomas.presentation.api.v1.diplomas import composition, print_package

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    c.drawString(50, 50, "background")
    c.save()
    return buffer.getvalue()


def _template_with_pdf(name: str) -> TemplateModel:
    template = TemplateModel.objects.create(name=name)
    key = default_storage.save(
        f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf())
    )
    TemplateDocumentModel.objects.create(
        template=template, file_reference=f"/media/{key}", page_count=1
    )
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
            },
        ],
    )
    return template


def _competition() -> CompetitionModel:
    return CompetitionModel.objects.create(
        title="Восходящие таланты",
        season="2026",
        organizer_id=uuid.uuid4(),
        status="PUBLISHED",
        competition_start=date(2026, 5, 15),
    )


def _submission(competition: CompetitionModel, name: str, category: CategoryModel) -> SubmissionModel:
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": name, "member_count": 1}],
        performance={"title": "Этюд", "nomination_id": str(category.id)},
    )


def _assign(competition: CompetitionModel, category: CategoryModel, template: TemplateModel) -> None:
    composition.create_assignment(
        competition_id=str(competition.id),
        category_id=str(category.id),
        template_id=str(template.id),
    )


def test_generation_uses_each_nominations_own_template() -> None:
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    dance = CategoryModel.objects.create(competition=competition, name="Танец")
    vocals_template = _template_with_pdf("Вокал A4")
    dance_template = _template_with_pdf("Танец A4")
    _assign(competition, vocals, vocals_template)
    _assign(competition, dance, dance_template)
    sub_vocals = _submission(competition, "Иванов Иван", vocals)
    sub_dance = _submission(competition, "Петров Пётр", dance)

    # Empty categoryIds → all assigned nominations.
    job = print_package.start_print_package(competition_id=competition.id, category_ids=[])

    assert job["status"] == "COMPLETED"
    assert job["created"] == 2
    assert job["skipped"] == 0

    by_submission = {
        str(d.submission_id): d for d in DiplomaModel.objects.filter(competition_id=competition.id)
    }
    assert str(by_submission[str(sub_vocals.id)].template_id) == str(vocals_template.id)
    assert str(by_submission[str(sub_dance.id)].template_id) == str(dance_template.id)
    for diploma in by_submission.values():
        assert diploma.status == DiplomaStatus.GENERATED.value
        assert diploma.print_pdf_path


def test_generation_for_selected_nominations_only() -> None:
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    dance = CategoryModel.objects.create(competition=competition, name="Танец")
    _assign(competition, vocals, _template_with_pdf("Вокал A4"))
    _assign(competition, dance, _template_with_pdf("Танец A4"))
    _submission(competition, "Иванов Иван", vocals)
    _submission(competition, "Петров Пётр", dance)

    job = print_package.start_print_package(
        competition_id=competition.id, category_ids=[str(vocals.id)]
    )

    assert job["created"] == 1  # only the vocals submission
    assert DiplomaModel.objects.filter(competition_id=competition.id).count() == 1


def test_summary_breaks_down_by_nomination() -> None:
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    dance = CategoryModel.objects.create(competition=competition, name="Танец")
    theatre = CategoryModel.objects.create(competition=competition, name="Театр")
    _assign(competition, vocals, _template_with_pdf("Вокал A4"))
    # theatre has a template assigned but no uploaded PDF → not ready.
    _assign(competition, theatre, TemplateModel.objects.create(name="Театр (без PDF)"))
    # dance has submissions but no template assigned.
    _submission(competition, "Иванов Иван", vocals)
    _submission(competition, "Сидоров С", vocals)
    _submission(competition, "Петров Пётр", dance)
    _submission(competition, "Театров Т", theatre)

    summary = print_package.print_package_summary(competition.id)
    by_id = {row["categoryId"]: row for row in summary["nominations"]}

    assert by_id[str(vocals.id)]["templateName"] == "Вокал A4"
    assert by_id[str(vocals.id)]["ready"] is True
    assert by_id[str(vocals.id)]["submissions"] == 2
    assert by_id[str(vocals.id)]["willCreate"] == 2
    # Assigned template without a PDF: shown, but not ready and nothing to create.
    assert by_id[str(theatre.id)]["templateName"] == "Театр (без PDF)"
    assert by_id[str(theatre.id)]["ready"] is False
    assert by_id[str(theatre.id)]["willCreate"] == 0
    # No template at all.
    assert by_id[str(dance.id)]["templateId"] is None
    assert by_id[str(dance.id)]["ready"] is False
    assert by_id[str(dance.id)]["willCreate"] == 0


def test_zip_contains_a_pdf_per_generated_diploma() -> None:
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    _assign(competition, vocals, _template_with_pdf("Вокал A4"))
    _submission(competition, "Иванов Иван", vocals)
    _submission(competition, "Сидоров С", vocals)

    job = print_package.start_print_package(competition_id=competition.id, category_ids=[])

    zip_key = job["zipUrl"][len("/media/") :]
    with default_storage.open(zip_key, "rb") as handle:
        archive = zipfile.ZipFile(io.BytesIO(handle.read()))
    names = archive.namelist()
    assert len(names) == 2
    for name in names:
        assert archive.read(name).startswith(b"%PDF")


def test_force_rerenders_existing_print_pdfs() -> None:
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    _assign(competition, vocals, _template_with_pdf("Вокал A4"))
    _submission(competition, "Иванов Иван", vocals)

    first = print_package.start_print_package(competition_id=competition.id, category_ids=[])
    assert first["created"] == 1
    diploma = DiplomaModel.objects.get(competition_id=competition.id)
    version_after_first = diploma.version

    # Without force: existing diploma is skipped and its PDF is not re-rendered.
    plain = print_package.start_print_package(competition_id=competition.id, category_ids=[])
    assert plain["created"] == 0 and plain["skipped"] == 1
    diploma.refresh_from_db()
    assert diploma.version == version_after_first

    # With force: the existing diploma's print PDF is re-rendered (version bumps).
    forced = print_package.start_print_package(
        competition_id=competition.id, category_ids=[], force=True
    )
    assert forced["created"] == 0 and forced["skipped"] == 1
    diploma.refresh_from_db()
    assert diploma.version > version_after_first
    assert diploma.print_pdf_path


def test_no_assigned_template_raises() -> None:
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    _submission(competition, "Иванов Иван", vocals)

    with pytest.raises(PrintTemplateNotReadyError):
        print_package.start_print_package(competition_id=competition.id, category_ids=[])
