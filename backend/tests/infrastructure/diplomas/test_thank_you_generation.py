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
import zipfile
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel, DisciplineModel
from apps.diplomas.composition import build_issued_document_generation_service
from apps.diplomas.domain.document_types import DocumentType
from apps.diplomas.domain.exceptions import (
    PrintTemplateNotReadyError,
    TemplateNotAssignedError,
)
from apps.diplomas.infrastructure.models import (
    IssuedDocumentModel,
    TemplateDocumentModel,
    TemplateFieldModel,
    TemplateModel,
)
from apps.diplomas.presentation.api.v1.diplomas import composition, documents
from apps.diplomas.presentation.scope import Scope

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

    from apps.diplomas.application.issued_documents import IssuedDocumentResult

pytestmark = pytest.mark.django_db

#: One organization for everything this module builds. A template and the
#: competition it is used on have to belong to the same organizer now — the scoped
#: listings admit a row only when both sides match — so a fresh `uuid4()` per
#: competition would put them on opposite sides of the boundary.
_ORGANIZER = uuid.UUID("00000000-0000-4000-8000-0000000000a1")
_SCOPE = Scope.for_organization(_ORGANIZER)


_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)


def _key(reference: str) -> str:
    """The storage key behind a stored reference.

    References are URLs (``default_storage.url``), so a document named after "Петрова
    Ольга" is percent-encoded in the reference while the object is stored under the
    name as written.
    """
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


def _template(name: str, document_type: str, *, with_qr: bool = False) -> TemplateModel:
    """A template of one kind, with a backing PDF and a name field.

    ``with_qr`` inserts the QR row **directly**, bypassing
    :func:`replace_template_layout` — which now refuses a QR on a thank-you
    template. That is the point: it forges the layout a stale client or a
    pre-rule template could leave behind, so the render-time defence is exercised
    rather than the API validation that normally prevents it.
    """
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type=document_type, name=name)
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
    if with_qr:
        TemplateFieldModel.objects.create(
            template=template,
            page=1,
            type="qr_block",
            binding="diploma.number",
            x=0.6,
            y=0.8,
            width=0.32,
            height=0.1,
            sort_order=1,
            style={"fontSize": 9},
        )
    return template


def _competition() -> CompetitionModel:
    return CompetitionModel.objects.create(
        title="Восходящие таланты",
        season="2026",
        organizer_id=_ORGANIZER,
        status="PUBLISHED",
        venue_name="Москва",
        competition_start=date(2026, 5, 15),
    )


def _submission(
    competition: CompetitionModel,
    category: CategoryModel,
    name: str,
    *,
    teachers: list[dict[str, str]] | None = None,
    status: str = "ACCEPTED",
    discipline: DisciplineModel | None = None,
) -> SubmissionModel:
    """One entry. A thank-you letter is addressed to a teacher, so the default
    names one — an entry with no teacher yields no letters at all. ``ACCEPTED`` by
    default: only entries taken into the competition are issued documents."""
    performance: dict[str, Any] = {"title": "Этюд", "nomination_id": str(category.id)}
    if discipline is not None:
        performance["discipline_id"] = str(discipline.id)
    return SubmissionModel.objects.create(
        competition_id=competition.id,
        applicant_id=uuid.uuid4(),
        status=status,
        participants=[{"display_name": name, "member_count": 1}],
        teachers=[{"first_name": "Ольга", "last_name": "Петрова", "role": "Педагог"}] if teachers is None else teachers,
        performance=performance,
    )


def _assign(competition: CompetitionModel, category: CategoryModel, template: TemplateModel) -> None:
    composition.create_assignment(
        competition_id=str(competition.id),
        category_id=str(category.id),
        template_id=str(template.id),
        scope=_SCOPE,
    )


def _generate(competition: CompetitionModel, category: CategoryModel, *, force: bool = False) -> IssuedDocumentResult:
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

    def test_skips_entries_not_yet_in_the_competition(self) -> None:
        """A letter thanks a teacher for a performance, so it waits for the same
        commitment a diploma does — the filter lives in the shared snapshot source."""
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Принятая")
        _submission(competition, vocals, "Отменённая", status="CANCELLED")
        _submission(competition, vocals, "На доработке", status="REQUIRES_CORRECTION")
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))

        result = _generate(competition, vocals)

        assert result.created == 1
        # Not counted as "nobody to thank" either — those entries never entered the run.
        assert result.without_recipient == 0
        assert IssuedDocumentModel.objects.count() == 1

    def test_carries_no_number_and_no_qr(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        # A forged layout carrying a QR block (see `_template`) must still print
        # none: generation drops what the kind may not carry.
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU", with_qr=True))

        _generate(competition, vocals)

        row = IssuedDocumentModel.objects.get(document_type="THANK_YOU")
        key = _key(row.pdf_path)
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


class TestLayoutRules:
    def test_a_thank_you_template_cannot_be_given_diploma_fields(self) -> None:
        from apps.diplomas.domain.exceptions import FieldTypeNotAllowedError

        template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="THANK_YOU", name="Благодарность")

        with pytest.raises(FieldTypeNotAllowedError):
            composition.replace_template_layout(
                template_id=str(template.id),
                fields=[
                    {
                        "page": 1,
                        "type": "award_degree",
                        "binding": "award.degree",
                        "x": 0.1,
                        "y": 0.1,
                        "width": 0.5,
                        "height": 0.1,
                    }
                ],
            )

    def test_a_thank_you_template_accepts_its_own_fields(self) -> None:
        template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="THANK_YOU", name="Благодарность")

        layout = composition.replace_template_layout(
            template_id=str(template.id),
            fields=[
                {
                    "page": 1,
                    "type": field_type,
                    "binding": binding,
                    "x": 0.1,
                    "y": 0.1,
                    "width": 0.5,
                    "height": 0.1,
                }
                for field_type, binding in [
                    ("participant_name", "participant.display_name"),
                    ("teacher", "teacher.display_name"),
                    ("competition_name", "competition.title"),
                    ("competition_date", "competition.date"),
                    ("competition_city", "competition.city"),
                    ("free_text", ""),
                ]
            ],
        )

        assert len(layout["fields"]) == 6

    def test_a_diploma_template_still_accepts_everything(self) -> None:
        template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="DIPLOMA", name="Диплом")

        layout = composition.replace_template_layout(
            template_id=str(template.id),
            fields=[
                {
                    "page": 1,
                    "type": "award_degree",
                    "binding": "award.degree",
                    "x": 0.1,
                    "y": 0.1,
                    "width": 0.5,
                    "height": 0.1,
                },
                {
                    "page": 1,
                    "type": "qr_block",
                    "binding": "diploma.number",
                    "x": 0.6,
                    "y": 0.8,
                    "width": 0.3,
                    "height": 0.1,
                },
            ],
        )

        assert len(layout["fields"]) == 2


class TestAddressing:
    """A thank-you letter is addressed to a person, so the recipient shapes the run."""

    def _generate_for(self, teachers: list[dict[str, str]]) -> IssuedDocumentResult:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван", teachers=teachers)
        template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type="THANK_YOU", name="Благодарность")
        key = default_storage.save(f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf()))
        TemplateDocumentModel.objects.create(template=template, file_reference=f"/media/{key}", page_count=1)
        composition.replace_template_layout(
            template_id=str(template.id),
            fields=[
                {
                    "page": 1,
                    "type": "teacher",
                    "binding": "teacher.display_name",
                    "x": 0.1,
                    "y": 0.1,
                    "width": 0.8,
                    "height": 0.1,
                }
            ],
        )
        _assign(competition, vocals, template)
        return _generate(competition, vocals)

    def _text_of(self, row: IssuedDocumentModel) -> str:
        with default_storage.open(_key(row.pdf_path), "rb") as fh:
            return PdfReader(io.BytesIO(fh.read())).pages[0].extract_text()

    def test_prints_the_name_without_the_role(self) -> None:
        self._generate_for([{"first_name": "Ольга", "last_name": "Петрова", "role": "Педагог"}])

        row = IssuedDocumentModel.objects.get(document_type="THANK_YOU")
        text = self._text_of(row)
        assert "Петрова Ольга" in text
        # A diploma would print "Педагог: Петрова Ольга"; a letter thanks the person.
        assert "Педагог:" not in text
        assert row.recipient == "Петрова Ольга"

    def test_two_teachers_get_two_separate_letters(self) -> None:
        result = self._generate_for(
            [
                {"first_name": "Ольга", "last_name": "Петрова", "role": "Педагог"},
                {"first_name": "Иван", "last_name": "Сидоров", "role": "Концертмейстер"},
            ]
        )

        assert result.created == 2
        rows = {row.recipient: row for row in IssuedDocumentModel.objects.all()}
        assert set(rows) == {"Петрова Ольга", "Сидоров Иван"}

        # Each letter names only its own recipient — never the whole roster.
        petrova = self._text_of(rows["Петрова Ольга"])
        sidorov = self._text_of(rows["Сидоров Иван"])
        assert "Петрова Ольга" in petrova
        assert "Сидоров" not in petrova
        assert "Сидоров Иван" in sidorov
        assert "Петрова" not in sidorov

        # …and each is a distinct file, not one overwriting the other.
        assert rows["Петрова Ольга"].pdf_path != rows["Сидоров Иван"].pdf_path

    def test_each_letters_snapshot_holds_only_its_recipient(self) -> None:
        self._generate_for(
            [
                {"first_name": "Ольга", "last_name": "Петрова", "role": "Педагог"},
                {"first_name": "Иван", "last_name": "Сидоров", "role": "Концертмейстер"},
            ]
        )

        for row in IssuedDocumentModel.objects.all():
            names = [teacher["name"] for teacher in row.snapshot["teachers"]]
            assert names == [row.recipient]

    def test_an_entry_naming_nobody_yields_no_letter(self) -> None:
        result = self._generate_for([])

        # Nobody to thank, so nothing is issued — and it is counted, not silent.
        assert result.created == 0
        assert result.without_recipient == 1
        assert IssuedDocumentModel.objects.count() == 0

    def test_regeneration_does_not_duplicate_per_recipient(self) -> None:
        self._generate_for(
            [
                {"first_name": "Ольга", "last_name": "Петрова", "role": "Педагог"},
                {"first_name": "Иван", "last_name": "Сидоров", "role": "Концертмейстер"},
            ]
        )
        competition = CompetitionModel.objects.get()
        vocals = CategoryModel.objects.get()

        again = _generate(competition, vocals)

        assert (again.created, again.regenerated) == (0, 0)
        assert IssuedDocumentModel.objects.count() == 2


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

        by_template = {str(row.template_id): row.snapshot["participant"]["display_name"] for row in IssuedDocumentModel.objects.all()}
        # One teacher each, so one letter each.
        assert IssuedDocumentModel.objects.count() == 2
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

        assignments = {item["documentType"]: item["templateId"] for item in composition.list_assignments(scope=_SCOPE)}
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


class TestPrintableBundle:
    """The offline half: the same run can also hand back a ZIP to print from.

    Publication is unaffected — a letter reaches the cabinet on generation either
    way — so what these check is the archive: that it holds the nomination's whole
    set (not just what one run rendered) under names an organizer can sort by hand.
    """

    def _run(self, competition: CompetitionModel, categories: list[CategoryModel], *, bundle: bool) -> dict[str, Any]:
        return documents.generate_documents(
            competition_id=competition.id,
            category_ids=[category.id for category in categories],
            document_type="THANK_YOU",
            bundle=bundle,
        )

    def _entries(self, zip_url: str) -> list[str]:
        with (
            default_storage.open(_key(zip_url), "rb") as fh,
            zipfile.ZipFile(io.BytesIO(fh.read())) as archive,
        ):
            return sorted(archive.namelist())

    def test_archives_a_letter_per_recipient_grouped_by_nomination(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(
            competition,
            vocals,
            "Иванов Иван",
            teachers=[
                {"first_name": "Ольга", "last_name": "Петрова", "role": "Педагог"},
                {"first_name": "Иван", "last_name": "Сидоров", "role": "Концертмейстер"},
            ],
        )
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))

        summary = self._run(competition, [vocals], bundle=True)

        assert summary["created"] == 2
        assert summary["documents"] == 2
        # The unguessable segment between the kind and the filename is derived from
        # SECRET_KEY, so the test asserts the shape rather than recomputing the secret.
        assert summary["zipUrl"].startswith(f"/media/diplomas/documents/{competition.id}/thank_you/")
        assert summary["zipUrl"].endswith("/ThankYou.zip")
        # Addressed to the teacher, filed under the nomination, with the performance
        # named so a teacher thanked twice yields two distinguishable sheets.
        assert self._entries(summary["zipUrl"]) == [
            "Вокал/Петрова Ольга — Иванов Иван.pdf",
            "Вокал/Сидоров Иван — Иванов Иван.pdf",
        ]

    def test_a_repeat_run_archives_the_whole_set_it_did_not_regenerate(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        _submission(competition, vocals, "Петров Пётр")
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))

        self._run(competition, [vocals], bundle=False)
        again = self._run(competition, [vocals], bundle=True)

        # Nothing to redo, yet the archive is still the complete printable stack.
        assert (again["created"], again["regenerated"]) == (0, 0)
        assert again["documents"] == 2
        assert len(self._entries(again["zipUrl"])) == 2

    def test_no_archive_without_asking_and_none_when_there_is_nothing_to_print(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))
        empty = CategoryModel.objects.create(competition=competition, name="Хореография")
        _submission(competition, empty, "Без педагога", teachers=[])
        _assign(competition, empty, _template("Благодарность 2", "THANK_YOU"))

        plain = self._run(competition, [vocals], bundle=True)
        nothing = self._run(competition, [empty], bundle=True)

        assert plain["zipUrl"] is not None
        # A nomination naming nobody produces no letters, so there is no broken
        # download to hand over either.
        assert nothing["documents"] == 0
        assert nothing["zipUrl"] is None
        assert self._run(competition, [vocals], bundle=False)["zipUrl"] is None

    def test_namesakes_get_two_entries_rather_than_one_overwriting_the_other(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        # Two separate entries with the same performer name and the same teacher —
        # names are not unique, so the archive cannot rely on them being so.
        _submission(competition, vocals, "Иванов Иван")
        _submission(competition, vocals, "Иванов Иван")
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))

        summary = self._run(competition, [vocals], bundle=True)

        assert summary["documents"] == 2
        # Both letters survive: a duplicate name in a ZIP means one file replacing
        # the other on extraction.
        assert self._entries(summary["zipUrl"]) == [
            "Вокал/Петрова Ольга — Иванов Иван (2).pdf",
            "Вокал/Петрова Ольга — Иванов Иван.pdf",
        ]


class TestPublicationIsTheRunsChoice:
    """Generating for print is not publishing.

    An organizer who prepares sheets to print has decided nothing about what
    participants may see yet, so the two intents are separate runs — and the
    cabinet is only ever filled by the one that asks for it.
    """

    def _run(self, competition: CompetitionModel, category: CategoryModel, **kwargs: Any) -> dict[str, Any]:
        return documents.generate_documents(
            competition_id=competition.id,
            category_ids=[category.id],
            document_type="THANK_YOU",
            **kwargs,
        )

    def _fixture(self) -> tuple[CompetitionModel, CategoryModel]:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")
        _assign(competition, vocals, _template("Благодарность", "THANK_YOU"))
        return competition, vocals

    def test_a_print_run_generates_without_publishing(self) -> None:
        competition, vocals = self._fixture()

        summary = self._run(competition, vocals, bundle=True, publish=False)

        assert (summary["created"], summary["published"]) == (1, 0)
        row = IssuedDocumentModel.objects.get()
        # Complete and printable, but invisible: nothing reaches the cabinet.
        assert row.pdf_path
        assert row.published_at is None
        assert summary["zipUrl"] is not None

    def test_publishing_afterwards_needs_no_re_render(self) -> None:
        competition, vocals = self._fixture()
        self._run(competition, vocals, bundle=True, publish=False)

        summary = self._run(competition, vocals)

        # Nothing created and nothing re-rendered — the sheet the organizer may
        # already have printed is untouched; only its visibility changed.
        assert (summary["created"], summary["regenerated"]) == (0, 0)
        assert summary["published"] == 1
        assert IssuedDocumentModel.objects.get().published_at is not None

    def test_a_print_run_never_unpublishes_what_is_already_out(self) -> None:
        competition, vocals = self._fixture()
        self._run(competition, vocals)
        published_at = IssuedDocumentModel.objects.get().published_at

        # Re-rendering after a template fix must not pull the letter back out of
        # the cabinet, nor move its publication date.
        summary = self._run(competition, vocals, bundle=True, publish=False, force=True)

        assert summary["regenerated"] == 1
        assert IssuedDocumentModel.objects.get().published_at == published_at


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
        _assign(competition, vocals, TemplateModel.objects.create(organizer_id=_ORGANIZER, type="THANK_YOU", name="Без PDF"))

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


class TestNominationLevelTemplates:
    """A nomination inside a genre may be thanked on a sheet of its own — the jury
    that signs it is not the genre's."""

    def _nomination(self, competition: CompetitionModel, category: CategoryModel, name: str) -> DisciplineModel:
        return DisciplineModel.objects.create(competition=competition, category_id=category.id, name=name)

    def _assign_nomination(self, competition: CompetitionModel, discipline: DisciplineModel, template: TemplateModel) -> None:
        composition.create_assignments(
            competition_id=str(competition.id),
            discipline_ids=[str(discipline.id)],
            template_id=str(template.id),
            scope=_SCOPE,
        )

    def test_the_nominations_template_wins_over_the_genres(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        pop = self._nomination(competition, vocals, "Эстрадный вокал")
        blue = _template("Благодарность синяя", "THANK_YOU")
        gold = _template("Благодарность золотая", "THANK_YOU")
        _assign(competition, vocals, blue)
        self._assign_nomination(competition, pop, gold)
        _submission(competition, vocals, "Иванов Иван")
        _submission(competition, vocals, "Петров Пётр", discipline=pop)

        result = _generate(competition, vocals)

        assert result.created == 2
        by_template = {str(row.template_id): row.snapshot["participant"]["display_name"] for row in IssuedDocumentModel.objects.all()}
        assert by_template[str(blue.id)] == "Иванов Иван"
        assert by_template[str(gold.id)] == "Петров Пётр"

    def test_a_genre_with_no_default_counts_what_it_cannot_print(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        pop = self._nomination(competition, vocals, "Эстрадный вокал")
        self._assign_nomination(competition, pop, _template("Благодарность золотая", "THANK_YOU"))
        _submission(competition, vocals, "Иванов Иван")
        _submission(competition, vocals, "Петров Пётр", discipline=pop)

        result = _generate(competition, vocals)

        assert result.created == 1
        # The entry outside the covered nomination is reported, not silently dropped
        # and not raised over: assigning one nomination a sheet promises nothing for
        # the others.
        assert result.without_template == 1
        assert IssuedDocumentModel.objects.count() == 1

    def test_a_genre_with_nothing_assigned_at_either_level_still_raises(self) -> None:
        competition = _competition()
        vocals = CategoryModel.objects.create(competition=competition, name="Вокал")
        _submission(competition, vocals, "Иванов Иван")

        with pytest.raises(TemplateNotAssignedError):
            _generate(competition, vocals)
