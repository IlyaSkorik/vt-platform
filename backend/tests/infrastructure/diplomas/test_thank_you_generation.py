"""Integration tests for thank-you letter generation.

Exercises the whole non-registry path: the per-nomination assignment resolves a
``THANK_YOU`` template, the shared snapshot ACL supplies the data, the shared
renderer and storage produce the PDF, and the policy publishes it immediately.

The point of most of these is what a thank-you letter must *not* have — no QR, no
number, no degree — and that a nomination's diploma and thank-you templates are
independent of each other.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, date, datetime

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.composition import build_issued_document_generation_service
from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.exceptions import (
    PrintTemplateNotReadyError,
    TemplateNotAssignedError,
)
from apps.diplomas.infrastructure.models import (
    IssuedDocumentModel,
    TemplateDocumentModel,
    TemplateModel,
)
from apps.diplomas.presentation.api.v1.diplomas import composition

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    c.drawString(50, 50, "background")
    c.save()
    return buffer.getvalue()


def _template(name: str, document_type: str, *, with_qr: bool = False) -> TemplateModel:
    """A template of one kind, with a backing PDF and a name field."""
    template = TemplateModel.objects.create(type=document_type, name=name)
    key = default_storage.save(f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf()))
    TemplateDocumentModel.objects.create(template=template, file_reference=f"/media/{key}", page_count=1)
    fields: list[dict[str, object]] = [
        {
            "page": 1,
            "type": "participant_name",
            "binding": "participant.display_name",
            "x": 0.1,
            "y": 0.1,
            "width": 0.6,
            "height": 0.1,
        }
    ]
    if with_qr:
        fields.append(
            {
                "page": 1,
                "type": "qr_block",
                "binding": "diploma.number",
                "x": 0.6,
                "y": 0.8,
                "width": 0.32,
                "height": 0.1,
                "style": {"fontSize": 9},
            }
        )
    composition.replace_template_layout(template_id=str(template.id), fields=fields)
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


def _submission(competition: CompetitionModel, category: CategoryModel, name: str) -> SubmissionModel:
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="SUBMITTED",
        participants=[{"display_name": name, "member_count": 1}],
        teachers=[],
        performance={"title": "Этюд", "nomination_id": str(category.id)},
    )


def _assign(competition: CompetitionModel, category: CategoryModel, template: TemplateModel) -> None:
    composition.create_assignment(
        competition_id=str(competition.id),
        category_id=str(category.id),
        template_id=str(template.id),
    )


def _generate(competition: CompetitionModel, category: CategoryModel, *, force: bool = False):
    return build_issued_document_generation_service().generate_for_nomination(
        competition_id=competition.id,
        category_id=category.id,
        document_type=DocumentType.THANK_YOU,
        now=_NOW,
        force=force,
    )


class TestGeneration:
    def test_generates_a_published_letter_per_performance(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        _submission(competition, vocals, "Петров Пётр")
        _assign(competition, vocals, _template("Благодарность синяя", "THANK_YOU"))

        result = _generate(competition, vocals)

        assert result.created == 2
        rows = IssuedDocumentModel.objects.filter(document_type="THANK_YOU")
        assert rows.count() == 2
        for row in rows:
            # Published on generation — the organizer publishes nothing extra.
            assert row.published_at == _NOW
            assert row.pdf_path.startswith("/media/diplomas/documents/")

    def test_carries_no_number_and_no_qr(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        # Even a template that mistakenly carries a QR block must not print one.
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU", with_qr=True))

        _generate(competition, vocals)

        row = IssuedDocumentModel.objects.get(document_type="THANK_YOU")
        key = row.pdf_path.removeprefix("/media/")
        with default_storage.open(key, "rb") as fh:
            page = PdfReader(io.BytesIO(fh.read())).pages[0]
        # No embedded image: the QR block was dropped for an unverifiable kind.
        assert len(page.images) == 0
        text = page.extract_text()
        assert "Подлинность гарантирована!" not in text
        assert "VT-" not in text
        assert "Иванов Иван" in text

    def test_has_no_registry_row_and_no_token(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))

        _generate(competition, vocals)

        from apps.diplomas.infrastructure.models import DiplomaModel

        # A thank-you letter never enters the diploma register, so it can never be
        # verified — there is nothing to verify.
        assert DiplomaModel.objects.count() == 0
        row = IssuedDocumentModel.objects.get()
        assert not hasattr(row, "verification_token")

    def test_is_idempotent_unless_forced(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))

        first = _generate(competition, vocals)
        second = _generate(competition, vocals)
        forced = _generate(competition, vocals, force=True)

        assert (first.created, first.regenerated) == (1, 0)
        assert (second.created, second.regenerated) == (0, 0)
        assert (forced.created, forced.regenerated) == (0, 1)
        # One performance keeps exactly one letter throughout.
        assert IssuedDocumentModel.objects.count() == 1


class TestPerNominationTemplates:
    def test_each_nomination_uses_its_own_thank_you_design(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        dance = CategoryModel.objects.create(competition=competition, name="Хореография")
        _submission(competition, vocals, "Иванов Иван")
        _submission(competition, dance, "Петров Пётр")
        blue = _template("Благодарность синяя", "THANK_YOU")
        gold = _template("Благодарность золотая", "THANK_YOU")
        _assign(competition, vocals, blue)
        _assign(competition, dance, gold)

        _generate(competition, vocals)
        _generate(competition, dance)

        by_template = {
            str(row.template_id): row.snapshot["participant"]["display_name"]
            for row in IssuedDocumentModel.objects.all()
        }
        assert by_template[str(blue.id)] == "Иванов Иван"
        assert by_template[str(gold.id)] == "Петров Пётр"

    def test_a_nomination_holds_a_diploma_and_a_thank_you_template(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        diploma_template = _template("Диплом вокал", "DIPLOMA")
        thanks_template = _template("Благодарность синяя", "THANK_YOU")

        _assign(competition, vocals, diploma_template)
        # The diploma assignment must not block the thank-you assignment.
        _assign(competition, vocals, thanks_template)

        assignments = {item["documentType"]: item["templateId"] for item in composition.list_assignments()}
        assert assignments == {
            "DIPLOMA": str(diploma_template.id),
            "THANK_YOU": str(thanks_template.id),
        }

    def test_a_second_template_of_the_same_kind_conflicts(self) -> None:
        from apps.diplomas.domain.exceptions import AssignmentConflictError

        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _assign(competition, vocals, _template("Благодарность синяя", "THANK_YOU"))

        with pytest.raises(AssignmentConflictError):
            _assign(competition, vocals, _template("Благодарность золотая", "THANK_YOU"))


class TestPreconditions:
    def test_unassigned_nomination_is_refused(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")

        with pytest.raises(TemplateNotAssignedError):
            _generate(competition, vocals)

    def test_a_diploma_assignment_does_not_satisfy_the_thank_you_slot(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        _assign(competition, vocals, _template("Диплом вокал", "DIPLOMA"))

        # The slots are independent: a diploma template fills only the diploma slot.
        with pytest.raises(TemplateNotAssignedError):
            _generate(competition, vocals)

    def test_template_without_a_pdf_is_refused_before_anything_is_written(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        _assign(competition, vocals, TemplateModel.objects.create(type="THANK_YOU", name="Без PDF"))

        with pytest.raises(PrintTemplateNotReadyError):
            _generate(competition, vocals)

        assert IssuedDocumentModel.objects.count() == 0

    def test_the_diploma_kind_is_refused_by_this_service(self) -> None:
        from apps.diplomas.domain.exceptions import TemplateTypeMismatchError

        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")

        # Diplomas must go through the numbered print-package path.
        with pytest.raises(TemplateTypeMismatchError):
            build_issued_document_generation_service().generate_for_nomination(
                competition_id=competition.id,
                category_id=vocals.id,
                document_type=DocumentType.DIPLOMA,
                now=_NOW,
            )
