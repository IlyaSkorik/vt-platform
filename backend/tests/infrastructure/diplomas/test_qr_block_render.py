"""Integration tests for the QR block on a printed diploma.

The QR code is verified by *decoding it back to modules*: the image embedded in
the PDF is sampled at each module centre and compared with the matrix ``qrcode``
produces for the expected verification URL. If they match, a scanner reading the
printed code lands on ``<domain>/verify/<verificationToken>`` — which is what
"the QR opens the verification page" means in practice.

Covers the renderer in isolation and the full print-package path (number format,
QR contents, ZIP) end to end.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import date

import pytest
import qrcode
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.domain.value_objects import (
    DiplomaSnapshot,
    NominationSnapshot,
    ParticipantSnapshot,
)
from apps.diplomas.infrastructure.models import DiplomaModel, TemplateDocumentModel, TemplateModel
from apps.diplomas.infrastructure.pdf.qr import QR_BORDER, verification_url
from apps.diplomas.infrastructure.pdf.renderer import QR_VERIFICATION_TEXT, render_diploma_pdf
from apps.diplomas.presentation.api.v1.diplomas import composition, print_package

_DOMAIN = "https://diplomas.example.org"
_TOKEN = "AbC123-token_value"


@pytest.fixture(autouse=True)
def _verification_domain(settings):
    settings.DIPLOMA_VERIFICATION_BASE_URL = _DOMAIN


# --- QR probing helpers -----------------------------------------------------


def _expected_matrix(data: str) -> list[list[bool]]:
    """The module grid (border included) ``qrcode`` produces for ``data``."""
    code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=QR_BORDER,
    )
    code.add_data(data)
    code.make(fit=True)
    return [[bool(cell) for cell in row] for row in code.get_matrix()]


def _decoded_matrix(pdf: bytes, *, modules: int) -> list[list[bool]]:
    """Sample the PDF's single embedded image at each module centre.

    Sampling (rather than comparing raw bytes) keeps the assertion independent of
    how reportlab happens to encode or scale the image.
    """
    images = PdfReader(io.BytesIO(pdf)).pages[0].images
    assert len(images) == 1, "expected exactly one embedded image (the QR code)"
    grey = images[0].image.convert("L")
    width, _ = grey.size
    step = width / modules
    return [
        [
            grey.getpixel((int((column + 0.5) * step), int((row + 0.5) * step))) < 128
            for column in range(modules)
        ]
        for row in range(modules)
    ]


def _assert_qr_encodes(pdf: bytes, url: str) -> None:
    expected = _expected_matrix(url)
    assert _decoded_matrix(pdf, modules=len(expected)) == expected


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    c.drawString(50, 50, "background")
    c.save()
    return buffer.getvalue()


def _qr_field() -> dict[str, object]:
    return {
        "page": 1,
        "type": "qr_block",
        "binding": "diploma.number",
        "x": 0.6,
        "y": 0.8,
        "width": 0.32,
        "height": 0.1,
        "style": {"fontSize": 9, "textAlign": "left"},
    }


def _name_field() -> dict[str, object]:
    return {
        "page": 1,
        "type": "participant_name",
        "binding": "participant.display_name",
        "x": 0.1,
        "y": 0.1,
        "width": 0.6,
        "height": 0.1,
    }


def _snapshot() -> DiplomaSnapshot:
    return DiplomaSnapshot(
        participant=ParticipantSnapshot(display_name="Иванов Иван", age=12),
        nomination=NominationSnapshot(title="Вокал"),
    )


# --- The URL is configuration, not a constant -------------------------------


def test_verification_url_uses_the_configured_domain() -> None:
    assert verification_url(_TOKEN) == f"{_DOMAIN}/verify/{_TOKEN}"


def test_verification_url_tolerates_a_trailing_slash(settings) -> None:
    settings.DIPLOMA_VERIFICATION_BASE_URL = f"{_DOMAIN}/"

    assert verification_url(_TOKEN) == f"{_DOMAIN}/verify/{_TOKEN}"


# --- The renderer -----------------------------------------------------------


def test_qr_block_embeds_a_code_for_the_verification_url() -> None:
    url = verification_url(_TOKEN)

    pdf = render_diploma_pdf(
        fields=[_qr_field()],
        backing_pdf=_backing_pdf(),
        snapshot=_snapshot(),
        number="VT-2026-000001",
        verification_url=url,
    )

    _assert_qr_encodes(pdf, url)


def test_qr_block_prints_the_number_and_the_authenticity_text() -> None:
    pdf = render_diploma_pdf(
        fields=[_qr_field()],
        backing_pdf=_backing_pdf(),
        snapshot=_snapshot(),
        number="VT-2026-000042",
        verification_url=verification_url(_TOKEN),
    )

    # The caption is wrapped to the block's width, so compare on collapsed whitespace.
    text = " ".join(PdfReader(io.BytesIO(pdf)).pages[0].extract_text().split())
    assert "VT-2026-000042" in text
    assert QR_VERIFICATION_TEXT in text


def test_template_without_a_qr_block_gets_no_qr() -> None:
    pdf = render_diploma_pdf(
        fields=[_name_field()],
        backing_pdf=_backing_pdf(),
        snapshot=_snapshot(),
        number="VT-2026-000001",
        verification_url=verification_url(_TOKEN),
    )

    page = PdfReader(io.BytesIO(pdf)).pages[0]
    assert list(page.images) == []
    assert "Иванов Иван" in page.extract_text()


def test_qr_block_falls_back_to_text_without_a_verification_url() -> None:
    pdf = render_diploma_pdf(
        fields=[_qr_field()],
        backing_pdf=_backing_pdf(),
        snapshot=_snapshot(),
        number="VT-2026-000001",
    )

    page = PdfReader(io.BytesIO(pdf)).pages[0]
    assert list(page.images) == []
    assert "VT-2026-000001" in page.extract_text()


# --- The full print-package cycle -------------------------------------------


@pytest.mark.django_db
class TestPrintPackageCycle:
    """Create → number → PDF → QR → ZIP, through the real generation path."""

    @pytest.fixture(autouse=True)
    def _media_root(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)

    def _generate(self) -> tuple[DiplomaModel, dict]:
        competition = CompetitionModel.objects.create(
            title="Восходящие таланты",
            season="2026",
            organizer_id=uuid.uuid4(),
            status="PUBLISHED",
            competition_start=date(2026, 5, 15),
        )
        category = CategoryModel.objects.create(competition=competition, name="Вокал")
        template = TemplateModel.objects.create(name="Вокал A4")
        key = default_storage.save(
            f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf())
        )
        TemplateDocumentModel.objects.create(
            template=template, file_reference=f"/media/{key}", page_count=1
        )
        composition.replace_template_layout(
            template_id=str(template.id), fields=[_name_field(), _qr_field()]
        )
        composition.create_assignment(
            competition_id=str(competition.id),
            category_id=str(category.id),
            template_id=str(template.id),
        )
        SubmissionModel.objects.create(
            competition_id=competition.id,
            applicant_id=uuid.uuid4(),
            status="SUBMITTED",
            participants=[{"display_name": "Иванов Иван", "member_count": 1}],
            performance={"title": "Этюд", "nomination_id": str(category.id)},
        )

        job = print_package.start_print_package(competition_id=competition.id, category_ids=[])
        return DiplomaModel.objects.get(competition_id=competition.id), job

    def _stored(self, media_path: str) -> bytes:
        with default_storage.open(media_path[len("/media/") :], "rb") as handle:
            return handle.read()

    def test_generated_diploma_has_a_formatted_number_and_a_working_qr(self) -> None:
        diploma, job = self._generate()

        assert job["status"] == "COMPLETED"
        assert diploma.number == "VT-2026-000001"

        pdf = self._stored(diploma.print_pdf_path)
        # The QR resolves to this diploma's own verification page…
        _assert_qr_encodes(pdf, f"{_DOMAIN}/verify/{diploma.verification_token}")
        # …and the number printed under it is the diploma's number.
        assert diploma.number in PdfReader(io.BytesIO(pdf)).pages[0].extract_text()

    def test_zip_still_bundles_the_diploma_under_its_number(self) -> None:
        diploma, job = self._generate()

        archive = zipfile.ZipFile(io.BytesIO(self._stored(job["zipUrl"])))

        assert archive.namelist() == [f"{diploma.number}.pdf"]
        assert archive.read(f"{diploma.number}.pdf").startswith(b"%PDF")
