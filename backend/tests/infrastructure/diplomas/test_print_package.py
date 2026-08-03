"""Integration tests for mass print-package generation (per-nomination)."""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _media_root(settings: SettingsWrapper, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = str(tmp_path)


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    c.drawString(50, 50, "background")
    c.save()
    return buffer.getvalue()


def _template_with_pdf(name: str, document_type: str = "DIPLOMA") -> TemplateModel:
    template = TemplateModel.objects.create(type=document_type, name=name)
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


def _submission(
    competition: CompetitionModel,
    name: str,
    category: CategoryModel,
    teachers: list[dict[str, str]] | None = None,
    status: str = "ACCEPTED",
) -> SubmissionModel:
    """One entry. ``ACCEPTED`` by default — only entries taken into the competition
    are printed, so anything earlier would be invisible to generation."""
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status=status,
        participants=[{"display_name": name, "member_count": 1}],
        performance={"title": "Этюд", "nomination_id": str(category.id)},
        teachers=teachers or [],
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

    by_submission = {str(d.submission_id): d for d in DiplomaModel.objects.filter(competition_id=competition.id)}
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

    job = print_package.start_print_package(competition_id=competition.id, category_ids=[str(vocals.id)])

    assert job["created"] == 1  # only the vocals submission
    assert DiplomaModel.objects.filter(competition_id=competition.id).count() == 1


@pytest.mark.parametrize(
    "status",
    ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "REQUIRES_CORRECTION", "APPROVED", "WAITING_PAYMENT", "PAID", "CANCELLED"],
)
def test_an_entry_not_yet_in_the_competition_is_not_printed(status: str) -> None:
    """A diploma attests taking part, so it waits until the entry is committed.

    Everything before ``ACCEPTED`` is a decision not yet made, and ``CANCELLED`` is
    one made the other way. The register is immutable once written, so an entry that
    may still vanish must not get a numbered diploma.
    """
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    _assign(competition, vocals, _template_with_pdf("Вокал A4"))
    _submission(competition, "Иванов Иван", vocals, status=status)

    job = print_package.start_print_package(competition_id=competition.id, category_ids=[])

    assert job["created"] == 0
    assert DiplomaModel.objects.filter(competition_id=competition.id).count() == 0
    # And it is not promised in the summary either.
    summary = print_package.print_package_summary(competition.id)
    by_id = {row["categoryId"]: row for row in summary["nominations"]}
    assert by_id[str(vocals.id)]["submissions"] == 0
    assert by_id[str(vocals.id)]["diploma"]["willCreate"] == 0


@pytest.mark.parametrize("status", ["ACCEPTED", "SCHEDULED", "COMPLETED"])
def test_an_entry_in_the_competition_is_printed(status: str) -> None:
    """From ``ACCEPTED`` on the entry cannot be cancelled and its content is frozen —
    being scheduled or already performed does not take it out of the print run."""
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    _assign(competition, vocals, _template_with_pdf("Вокал A4"))
    _submission(competition, "Иванов Иван", vocals, status=status)

    job = print_package.start_print_package(competition_id=competition.id, category_ids=[])

    assert job["created"] == 1


def test_print_package_never_targets_a_thank_you_template() -> None:
    """A nomination's thank-you template is not a print-package target.

    Assignments are keyed by (nomination, type); resolving them by nomination
    alone let the older row win, so a thank-you template could end up rendering
    the numbered diplomas.
    """
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    # The thank-you assignment is created *first*, so it is the older row.
    _assign(competition, vocals, _template_with_pdf("Вокал: благодарность", "THANK_YOU"))
    diploma_template = _template_with_pdf("Вокал A4")
    _assign(competition, vocals, diploma_template)

    targets = print_package.resolve_targets(competition.id, [])

    assert [str(target.template_id) for target in targets] == [str(diploma_template.id)]


def test_summary_breaks_down_by_nomination() -> None:
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    dance = CategoryModel.objects.create(competition=competition, name="Танец")
    theatre = CategoryModel.objects.create(competition=competition, name="Театр")
    _assign(competition, vocals, _template_with_pdf("Вокал A4"))
    # theatre has a template assigned but no uploaded PDF → not ready.
    _assign(competition, theatre, TemplateModel.objects.create(type="DIPLOMA", name="Театр (без PDF)"))
    # dance has submissions but no template assigned.
    _submission(competition, "Иванов Иван", vocals)
    _submission(competition, "Сидоров С", vocals)
    _submission(competition, "Петров Пётр", dance)
    _submission(competition, "Театров Т", theatre)

    summary = print_package.print_package_summary(competition.id)
    by_id = {row["categoryId"]: row for row in summary["nominations"]}

    assert by_id[str(vocals.id)]["diploma"]["templateName"] == "Вокал A4"
    assert by_id[str(vocals.id)]["diploma"]["ready"] is True
    assert by_id[str(vocals.id)]["submissions"] == 2
    assert by_id[str(vocals.id)]["diploma"]["willCreate"] == 2
    # Assigned template without a PDF: shown, but not ready and nothing to create.
    assert by_id[str(theatre.id)]["diploma"]["templateName"] == "Театр (без PDF)"
    assert by_id[str(theatre.id)]["diploma"]["ready"] is False
    assert by_id[str(theatre.id)]["diploma"]["willCreate"] == 0
    # No template at all.
    assert by_id[str(dance.id)]["diploma"]["templateId"] is None
    assert by_id[str(dance.id)]["diploma"]["ready"] is False
    assert by_id[str(dance.id)]["diploma"]["willCreate"] == 0


def test_summary_reports_each_document_type_separately() -> None:
    """A diploma template must never make a nomination look thank-you-ready.

    The two slots are independent: «Вокал» has both, «Танец» only a diploma. A
    single merged flag would offer «Танец» for a thank-you run and earn a 409.
    """
    competition = _competition()
    vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
    dance = CategoryModel.objects.create(competition=competition, name="Танец")
    _assign(competition, vocals, _template_with_pdf("Вокал A4"))
    _assign(competition, vocals, _template_with_pdf("Вокал: благодарность", "THANK_YOU"))
    _assign(competition, dance, _template_with_pdf("Танец A4"))
    # Two teachers → two letters, but a single diploma.
    _submission(
        competition,
        "Иванов Иван",
        vocals,
        teachers=[
            {"last_name": "Петрова", "first_name": "Ольга", "role": "Педагог"},
            {"last_name": "Сидоров", "first_name": "Пётр", "role": "Концертмейстер"},
        ],
    )
    # No teacher named → nobody to thank, so it is reported as unaddressable.
    _submission(competition, "Петров Пётр", dance)

    by_id = {row["categoryId"]: row for row in print_package.print_package_summary(competition.id)["nominations"]}

    assert by_id[str(vocals.id)]["diploma"]["willCreate"] == 1
    assert by_id[str(vocals.id)]["thankYou"]["templateName"] == "Вокал: благодарность"
    assert by_id[str(vocals.id)]["thankYou"]["ready"] is True
    assert by_id[str(vocals.id)]["thankYou"]["willCreate"] == 2
    assert by_id[str(vocals.id)]["thankYou"]["withoutRecipient"] == 0

    assert by_id[str(dance.id)]["diploma"]["ready"] is True
    assert by_id[str(dance.id)]["thankYou"]["templateId"] is None
    assert by_id[str(dance.id)]["thankYou"]["ready"] is False
    assert by_id[str(dance.id)]["thankYou"]["willCreate"] == 0
    assert by_id[str(dance.id)]["thankYou"]["withoutRecipient"] == 1


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
    forced = print_package.start_print_package(competition_id=competition.id, category_ids=[], force=True)
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
