"""Integration tests for individual diplomas — one per named member of a collective.

Exercises the whole path publication takes: an applicant names the people in their
ensemble, the nomination assigns an ``INDIVIDUAL_DIPLOMA`` template, and awarding the
protocol issues the collective's diploma **and** one diploma per person — each
numbered, verifiable, and carrying that member's own ФИО.

The point of most of these is what must stay true of the collective's diploma while
this happens: it keeps its number, it is still exactly one document, and an entry that
named nobody (or a nomination with no individual template) behaves precisely as it did
before the kind existed.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from urllib.parse import unquote

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.composition import build_diploma_award_service
from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.infrastructure.models import (
    DiplomaModel,
    TemplateDocumentModel,
    TemplateModel,
)
from apps.diplomas.presentation.api.v1.diplomas import composition

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

    from apps.diplomas.application.awarding import AwardOutcome

pytestmark = pytest.mark.django_db

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)

_ENSEMBLE = "Ансамбль «Созвездие»"
_ROSTER = ["Иванова Мария Петровна", "Петров Пётр Петрович", "Сидорова Анна Ильинична"]


def _key(reference: str) -> str:
    """The storage key behind a stored reference (references are URLs)."""
    return unquote(reference.removeprefix("/media/"))


@pytest.fixture(autouse=True)
def _media_root(settings: SettingsWrapper, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = str(tmp_path)


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    c.drawString(50, 50, "background")
    c.save()
    return buffer.getvalue()


def _template(name: str, document_type: str, *, with_member: bool = False) -> TemplateModel:
    """A template of one kind, with a backing PDF, the performer's name, and — for an
    individual diploma — the one field that makes it individual."""
    template = TemplateModel.objects.create(type=document_type, name=name)
    key = default_storage.save(f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf()))
    TemplateDocumentModel.objects.create(template=template, file_reference=f"/media/{key}", page_count=1)
    fields = [
        {"page": 1, "type": "participant_name", "binding": "participant.display_name", "x": 0.1, "y": 0.1, "width": 0.6, "height": 0.1},
        {"page": 1, "type": "award_degree", "binding": "award.degree", "x": 0.1, "y": 0.3, "width": 0.6, "height": 0.1},
    ]
    if with_member:
        fields.append({"page": 1, "type": "member_name", "binding": "member.full_name", "x": 0.1, "y": 0.5, "width": 0.6, "height": 0.1})
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


def _submission(
    competition: CompetitionModel,
    category: CategoryModel,
    name: str = _ENSEMBLE,
    *,
    members: list[str] | None = None,
) -> SubmissionModel:
    """One accepted entry for a collective, optionally naming the people in it."""
    participant = {"display_name": name, "member_count": len(members) if members else 12}
    if members is not None:
        participant["members"] = members
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status="ACCEPTED",
        participants=[participant],
        teachers=[{"first_name": "Ольга", "last_name": "Петрова", "role": "Педагог"}],
        performance={"title": "Этюд", "nomination_id": str(category.id)},
    )


def _assign(competition: CompetitionModel, category: CategoryModel, template: TemplateModel) -> None:
    # Which slot the assignment fills is derived from the template's own type.
    composition.create_assignment(
        competition_id=str(competition.id),
        category_id=str(category.id),
        template_id=str(template.id),
    )


def _award(
    competition: CompetitionModel,
    category: CategoryModel,
    submission: SubmissionModel,
    degree: str = "Лауреат I степени",
) -> list[AwardOutcome]:
    return build_diploma_award_service().award(
        competition_id=competition.id,
        category_id=category.id,
        awards=[(submission.id, degree)],
        now=_NOW,
    )


def _text(reference: str) -> str:
    with default_storage.open(_key(reference), "rb") as fh:
        return PdfReader(io.BytesIO(fh.read())).pages[0].extract_text()


def _individuals() -> list[DiplomaModel]:
    return list(DiplomaModel.objects.filter(document_type="INDIVIDUAL_DIPLOMA").order_by("recipient"))


@pytest.fixture
def setup() -> tuple[CompetitionModel, CategoryModel]:
    competition = _competition()
    return competition, CategoryModel.objects.create(competition=competition, name="Вокал")


class TestIssuing:
    def test_issues_one_diploma_per_named_member(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))

        outcomes = _award(competition, vocals, submission)

        assert [outcome.individual_count for outcome in outcomes] == [len(_ROSTER)]
        # The collective's own diploma is still exactly one document.
        assert DiplomaModel.objects.filter(document_type="DIPLOMA").count() == 1
        assert [row.recipient for row in _individuals()] == sorted(_ROSTER)

    def test_each_member_gets_their_own_number_token_and_pdf(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))

        _award(competition, vocals, submission)

        rows = _individuals()
        # Every one of them is a register document in its own right — a shared number
        # or token would make one child's diploma verify as another's.
        assert len({row.number for row in rows}) == len(rows)
        assert len({row.verification_token for row in rows}) == len(rows)
        assert len({row.official_pdf_path for row in rows}) == len(rows)
        for row in rows:
            assert row.number.startswith("VT-2026-")
            assert row.status == "ISSUED"
            assert row.issued_at == _NOW

    def test_prints_the_member_the_collective_and_the_degree(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))

        _award(competition, vocals, submission)

        first = _individuals()[0]
        printed = _text(first.official_pdf_path)
        # An individual diploma is the collective's diploma with one more line on it:
        # the ensemble and the award are still on it, the member is added.
        assert first.recipient in printed
        assert _ENSEMBLE in printed
        assert "Лауреат I степени" in printed

    def test_the_collective_sheet_names_no_member(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))

        _award(competition, vocals, submission)

        collective = DiplomaModel.objects.get(document_type="DIPLOMA")
        printed = _text(collective.official_pdf_path)
        assert _ENSEMBLE in printed
        for name in _ROSTER:
            assert name not in printed


class TestOptingOut:
    def test_an_entry_that_named_nobody_gets_none(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        """Naming the roster is the request; leaving it empty is not asking."""
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))

        outcomes = _award(competition, vocals, submission)

        assert outcomes[0].individual_count == 0
        assert not _individuals()
        # …and the collective's diploma is issued exactly as before.
        assert DiplomaModel.objects.get(document_type="DIPLOMA").official_pdf_path

    def test_a_nomination_without_an_individual_template_issues_none(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))

        outcomes = _award(competition, vocals, submission)

        # The organizer has not designed that sheet; the roster costs the collective's
        # diploma nothing.
        assert outcomes[0].individual_count == 0
        assert not _individuals()
        assert DiplomaModel.objects.get(document_type="DIPLOMA").official_pdf_path

    def test_one_nominations_individual_template_does_not_reach_another(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        dance = CategoryModel.objects.create(competition=competition, name="Хореография")
        diplomas = _template("Диплом", "DIPLOMA")
        composition.create_assignments(
            competition_id=str(competition.id),
            category_ids=[str(vocals.id), str(dance.id)],
            template_id=str(diplomas.id),
        )
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))
        dancers = _submission(competition, dance, "Ансамбль «Ритм»", members=_ROSTER)

        outcomes = _award(competition, dance, dancers)

        assert outcomes[0].individual_count == 0
        assert not _individuals()


class TestRepublishing:
    def test_a_corrected_degree_re_renders_the_same_diplomas(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))
        _award(competition, vocals, submission)
        before = {row.recipient: (row.number, row.verification_token, row.official_pdf_path) for row in _individuals()}

        outcomes = _award(competition, vocals, submission, degree="Лауреат II степени")

        assert outcomes[0].individual_count == len(_ROSTER)
        rows = _individuals()
        # No second set of documents, and every child keeps the URL they already hold.
        assert len(rows) == len(_ROSTER)
        assert {row.recipient: (row.number, row.verification_token, row.official_pdf_path) for row in rows} == before
        assert "Лауреат II степени" in _text(rows[0].official_pdf_path)

    def test_a_member_named_after_publication_is_added(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER[:2])
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))
        _award(competition, vocals, submission)

        # The organizer corrected the roster and re-published.
        submission.participants = [{"display_name": _ENSEMBLE, "member_count": 3, "members": _ROSTER}]
        submission.save(update_fields=["participants"])
        outcomes = _award(competition, vocals, submission)

        assert outcomes[0].individual_count == len(_ROSTER)
        assert [row.recipient for row in _individuals()] == sorted(_ROSTER)


class TestCabinet:
    def test_the_member_diplomas_appear_in_my_documents(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        from apps.diplomas.composition import build_participant_documents_read_service

        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))
        _award(competition, vocals, submission)

        documents = build_participant_documents_read_service().list_for_applicant(submission.applicant_id)

        kinds = [document.document_type for document in documents]
        assert kinds == [DocumentType.DIPLOMA, *[DocumentType.INDIVIDUAL_DIPLOMA] * len(_ROSTER)]
        # The recipient is what tells three otherwise identical rows apart.
        individual = [document for document in documents if document.document_type is DocumentType.INDIVIDUAL_DIPLOMA]
        assert sorted(document.recipient for document in individual) == sorted(_ROSTER)
        assert all(document.number and document.degree == "Лауреат I степени" for document in individual)


class TestVerification:
    def test_a_member_diploma_verifies_as_itself(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        from apps.diplomas.composition import build_diploma_verification_read_service

        competition, vocals = setup
        submission = _submission(competition, vocals, members=_ROSTER)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))
        _award(competition, vocals, submission)

        row = _individuals()[0]
        view = build_diploma_verification_read_service().get_by_token(row.verification_token)

        # The public page is what the QR on that child's sheet leads to; a diploma that
        # did not verify would be worthless to them.
        assert view is not None
        assert view.number == row.number
        assert view.degree == "Лауреат I степени"
