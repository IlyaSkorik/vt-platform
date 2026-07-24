"""Integration tests for mass print-package generation (create → render → ZIP)."""

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
from apps.diplomas.application.services import DiplomaService
from apps.diplomas.domain.exceptions import PrintTemplateNotReadyError
from apps.diplomas.domain.value_objects import DiplomaStatus
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource
from apps.diplomas.infrastructure.models import DiplomaModel, TemplateDocumentModel, TemplateModel
from apps.diplomas.infrastructure.repositories import DjangoDiplomaRepository
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


def _template_with_pdf() -> TemplateModel:
    template = TemplateModel.objects.create(name="Шаблон")
    key = default_storage.save(f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf()))
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
            {
                "page": 1,
                "type": "award_degree",
                "binding": "award.degree",
                "x": 0.1,
                "y": 0.3,
                "width": 0.6,
                "height": 0.1,
            },
            {
                "page": 1,
                "type": "nomination_block",
                "binding": "nomination.block",
                "config": {"parts": ["title", "discipline"], "prefix": "Номинация:"},
                "x": 0.1,
                "y": 0.5,
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
        venue_name="Москва",
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


def test_generate_print_package_creates_renders_and_zips() -> None:
    competition = _competition()
    category = CategoryModel.objects.create(competition=competition, name="Вокал")
    template = _template_with_pdf()
    sub_a = _submission(competition, "Иванов Иван", category)
    _submission(competition, "Петров Пётр", category)
    # sub_a already has a diploma → it is skipped for creation but still printed.
    DiplomaService(
        repository=DjangoDiplomaRepository(),
        snapshots=DjangoDiplomaSnapshotSource(),
    ).create_diploma(submission_id=sub_a.id, template_id=template.id, now=_NOW)

    result = print_package.build_batch_service().generate_print_package(
        competition_id=competition.id, template_id=template.id, now=_NOW
    )

    assert result.created == 1  # only sub_b
    assert result.skipped == 1  # sub_a existed
    assert result.zip_path.startswith("/media/")

    diplomas = DiplomaModel.objects.filter(competition_id=competition.id)
    assert diplomas.count() == 2
    for diploma in diplomas:
        assert diploma.print_pdf_path
        assert diploma.status == DiplomaStatus.GENERATED.value

    # The ZIP holds one valid PDF per diploma.
    zip_key = result.zip_path[len("/media/") :]
    with default_storage.open(zip_key, "rb") as handle:
        archive = zipfile.ZipFile(io.BytesIO(handle.read()))
    names = archive.namelist()
    assert len(names) == 2
    for name in names:
        assert name.endswith(".pdf")
        assert archive.read(name).startswith(b"%PDF")


def test_print_package_requires_a_template_pdf() -> None:
    competition = _competition()
    template = TemplateModel.objects.create(name="Без PDF")

    service = print_package.build_batch_service()
    with pytest.raises(PrintTemplateNotReadyError):
        service.generate_print_package(
            competition_id=competition.id, template_id=template.id, now=_NOW
        )


def test_start_print_package_runs_job_to_completion() -> None:
    competition = _competition()
    category = CategoryModel.objects.create(competition=competition, name="Вокал")
    template = _template_with_pdf()
    _submission(competition, "Иванов Иван", category)

    # Eager Celery (test settings) runs the task inline, so the job is done.
    job = print_package.start_print_package(competition_id=competition.id, template_id=template.id)

    assert job["status"] == "COMPLETED"
    assert job["created"] == 1
    assert job["skipped"] == 0
    assert job["zipUrl"].startswith("/media/")
    assert job["error"] is None
