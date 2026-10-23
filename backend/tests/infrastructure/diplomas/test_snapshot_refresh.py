"""Перевыпуск дипломов, разошедшихся со своими заявками.

Поводом был случай на фестивале: организатор вписал учреждение за участника уже
после того, как дипломы сгенерировались, и исправление не дошло ни до PDF, ни до
кабинета, ни до страницы проверки по QR — снимок к тому моменту был заморожен.

Проверяется в первую очередь не то, что исправление доходит (это одна проверка),
а то, чего перевыпуск не имеет права сделать: тронуть диплом, который не менялся,
потерять степень, переименовать ребёнка в индивидуальном дипломе, сменить номер,
токен или ссылку, которую участник уже держит, — и уронить всю пачку из-за одного
сломанного шаблона.
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
from django.core.management import call_command
from django.core.management.base import CommandError
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import CategoryModel
from apps.diplomas.application.refresh import RefreshOutcome, RefreshStatus
from apps.diplomas.composition import build_diploma_award_service, build_diploma_snapshot_refresh_service
from apps.diplomas.infrastructure.models import DiplomaModel, TemplateDocumentModel, TemplateModel
from apps.diplomas.infrastructure.repositories import DjangoDiplomaRepository
from apps.diplomas.presentation.api.v1.diplomas import composition
from apps.diplomas.presentation.scope import Scope

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_django.fixtures import SettingsWrapper

pytestmark = pytest.mark.django_db

_ORGANIZER = uuid.UUID("00000000-0000-4000-8000-0000000000b2")
_SCOPE = Scope.for_organization(_ORGANIZER)
_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
_LATER = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
_SCHOOL = "Гимназия №3"


@pytest.fixture(autouse=True)
def _media_root(settings: SettingsWrapper, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = str(tmp_path)


def _key(reference: str) -> str:
    return unquote(reference.removeprefix("/media/"))


def _backing_pdf() -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(595.0, 842.0))
    page.drawString(50, 50, "background")
    page.save()
    return buffer.getvalue()


def _template(name: str, document_type: str, *, with_member: bool = False) -> TemplateModel:
    """Шаблон, печатающий учреждение, — иначе проверять в PDF нечего."""
    template = TemplateModel.objects.create(organizer_id=_ORGANIZER, type=document_type, name=name)
    key = default_storage.save(f"diplomas/templates/{template.id}/bg.pdf", ContentFile(_backing_pdf()))
    TemplateDocumentModel.objects.create(template=template, file_reference=f"/media/{key}", page_count=1)
    fields = [
        {"page": 1, "type": "participant_name", "binding": "participant.display_name", "x": 0.1, "y": 0.1, "width": 0.6, "height": 0.1},
        {"page": 1, "type": "organization", "binding": "organization.name", "x": 0.1, "y": 0.25, "width": 0.6, "height": 0.1},
        {"page": 1, "type": "award_degree", "binding": "award.degree", "x": 0.1, "y": 0.4, "width": 0.6, "height": 0.1},
    ]
    if with_member:
        fields.append({"page": 1, "type": "member_name", "binding": "member.full_name", "x": 0.1, "y": 0.55, "width": 0.6, "height": 0.1})
    composition.replace_template_layout(template_id=str(template.id), fields=fields)
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


def _submission(competition: CompetitionModel, category: CategoryModel, *, members: list[str] | None = None) -> SubmissionModel:
    """Заявка без учреждения — его организатор впишет позже, как это и было."""
    participant: dict[str, object] = {"display_name": "Иванова Анна", "member_count": len(members) if members else 1}
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
    composition.create_assignment(
        competition_id=str(competition.id),
        category_id=str(category.id),
        template_id=str(template.id),
        scope=_SCOPE,
    )


def _award(competition: CompetitionModel, category: CategoryModel, submission: SubmissionModel, degree: str = "Лауреат I степени") -> None:
    build_diploma_award_service().award(
        competition_id=competition.id,
        category_id=category.id,
        awards=[(submission.id, degree)],
        now=_NOW,
    )


def _correct_organization(submission: SubmissionModel, name: str = _SCHOOL) -> None:
    """Организатор вписывает учреждение за участника — уже после выпуска диплома."""
    participants = list(submission.participants)
    participants[0]["organization_name"] = name
    submission.participants = participants
    submission.save(update_fields=["participants"])


def _refresh(competition: CompetitionModel, *, apply: bool) -> list[RefreshOutcome]:
    diplomas = DjangoDiplomaRepository().list_by_competition(competition.id)
    return build_diploma_snapshot_refresh_service().refresh(diplomas, now=_LATER, apply=apply)


def _text(reference: str) -> str:
    with default_storage.open(_key(reference), "rb") as handle:
        return PdfReader(io.BytesIO(handle.read())).pages[0].extract_text()


@pytest.fixture
def setup() -> tuple[CompetitionModel, CategoryModel]:
    competition = _competition()
    return competition, CategoryModel.objects.create(competition=competition, name="Вокал")


class TestRefreshing:
    def test_an_organization_added_after_the_diploma_was_issued_reaches_the_pdf(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission)
        before = DiplomaModel.objects.get(document_type="DIPLOMA")
        assert _SCHOOL not in _text(before.official_pdf_path)

        _correct_organization(submission)
        outcomes = _refresh(competition, apply=True)

        assert [outcome.status for outcome in outcomes] == [RefreshStatus.UPDATED]
        after = DiplomaModel.objects.get(pk=before.pk)
        assert after.snapshot["organization"]["name"] == _SCHOOL
        assert _SCHOOL in _text(after.official_pdf_path)

    def test_the_document_stays_the_same_document(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        # Номер напечатан на бумаге, токен зашит в QR, ссылка уже у участника.
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission)
        before = DiplomaModel.objects.get(document_type="DIPLOMA")

        _correct_organization(submission)
        _refresh(competition, apply=True)

        after = DiplomaModel.objects.get(pk=before.pk)
        assert after.number == before.number
        assert after.verification_token == before.verification_token
        assert after.official_pdf_path == before.official_pdf_path
        assert after.issued_at == before.issued_at
        assert after.status == "ISSUED"

    def test_the_degree_survives(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission, degree="Гран-при")

        _correct_organization(submission)
        _refresh(competition, apply=True)

        row = DiplomaModel.objects.get(document_type="DIPLOMA")
        assert row.snapshot["award"]["degree"] == "Гран-при"
        assert "Гран-при" in _text(row.official_pdf_path)

    def test_a_diploma_that_has_not_changed_is_not_touched_at_all(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        # Главное требование: перевыпуск после правки одного учреждения не должен
        # переписать весь реестр — иначе по журналу документов больше не видно, что
        # в нём действительно менялось.
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission)
        before = DiplomaModel.objects.get(document_type="DIPLOMA")

        outcomes = _refresh(competition, apply=True)

        after = DiplomaModel.objects.get(pk=before.pk)
        assert [outcome.status for outcome in outcomes] == [RefreshStatus.UNCHANGED]
        assert after.version == before.version
        assert after.updated_at == before.updated_at

    def test_a_dry_run_writes_nothing(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission)
        before = DiplomaModel.objects.get(document_type="DIPLOMA")

        _correct_organization(submission)
        outcomes = _refresh(competition, apply=False)

        after = DiplomaModel.objects.get(pk=before.pk)
        assert [outcome.status for outcome in outcomes] == [RefreshStatus.PLANNED]
        assert after.version == before.version
        assert after.snapshot == before.snapshot
        assert _SCHOOL not in _text(after.official_pdf_path)

    def test_the_report_names_the_field_that_moved(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission)

        _correct_organization(submission)
        [outcome] = _refresh(competition, apply=False)

        assert [change.field for change in outcome.changes] == ["Учреждение"]
        assert _SCHOOL in outcome.changes[0].after


class TestIndividualDiplomas:
    def test_each_member_keeps_their_own_name(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        # Индивидуальный диплом — снимок коллектива, адресованный одному ребёнку.
        # Пересборка из заявки о нём не знает, и ошибка здесь превратила бы три
        # детских диплома в три копии ансамблевого.
        competition, vocals = setup
        roster = ["Иванова Мария", "Петров Пётр", "Сидорова Анна"]
        submission = _submission(competition, vocals, members=roster)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _assign(competition, vocals, _template("Диплом участнику", "INDIVIDUAL_DIPLOMA", with_member=True))
        _award(competition, vocals, submission)

        _correct_organization(submission)
        outcomes = _refresh(competition, apply=True)

        assert all(outcome.status is RefreshStatus.UPDATED for outcome in outcomes)
        rows = list(DiplomaModel.objects.filter(document_type="INDIVIDUAL_DIPLOMA").order_by("recipient"))
        assert [row.recipient for row in rows] == sorted(roster)
        for row in rows:
            assert row.snapshot["member"]["full_name"] == row.recipient
            assert row.snapshot["organization"]["name"] == _SCHOOL
            assert row.recipient in _text(row.official_pdf_path)


class TestFailuresDoNotSpread:
    def test_a_missing_template_skips_that_diploma_untouched(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        # Снимок без перерисованного PDF — это кабинет, который показывает одно, и
        # файл, в котором написано другое. Лучше не трогать совсем.
        competition, vocals = setup
        submission = _submission(competition, vocals)
        template = _template("Диплом", "DIPLOMA")
        _assign(competition, vocals, template)
        _award(competition, vocals, submission)
        before = DiplomaModel.objects.get(document_type="DIPLOMA")
        TemplateDocumentModel.objects.filter(template=template).update(deleted_at=_LATER)

        _correct_organization(submission)
        [outcome] = _refresh(competition, apply=True)

        after = DiplomaModel.objects.get(pk=before.pk)
        assert outcome.status is RefreshStatus.SKIPPED
        assert outcome.reason is not None
        assert after.snapshot == before.snapshot
        assert after.version == before.version

    def test_a_deleted_submission_is_skipped(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission)
        SubmissionModel.objects.filter(pk=submission.pk).update(deleted_at=_LATER)

        [outcome] = _refresh(competition, apply=True)

        assert outcome.status is RefreshStatus.SKIPPED
        assert "заявка удалена" in (outcome.reason or "")

    def test_one_broken_diploma_does_not_stop_the_others(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        healthy = _submission(competition, vocals)
        broken = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, healthy)
        _award(competition, vocals, broken)
        _correct_organization(healthy)
        _correct_organization(broken)
        SubmissionModel.objects.filter(pk=broken.pk).update(deleted_at=_LATER)

        outcomes = _refresh(competition, apply=True)

        statuses = sorted(outcome.status.value for outcome in outcomes)
        assert statuses == ["SKIPPED", "UPDATED"]
        assert DiplomaModel.objects.get(submission_id=healthy.id).snapshot["organization"]["name"] == _SCHOOL


class TestCommand:
    """``refresh_diploma_snapshots`` — то, что делает запуск на проде безопасным."""

    def test_without_apply_it_only_reports(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission)
        before = DiplomaModel.objects.get(document_type="DIPLOMA")
        _correct_organization(submission)

        output = io.StringIO()
        call_command("refresh_diploma_snapshots", f"--competition={competition.id}", stdout=output)

        after = DiplomaModel.objects.get(pk=before.pk)
        assert after.snapshot == before.snapshot
        assert "Учреждение" in output.getvalue()
        assert "--apply" in output.getvalue()

    def test_apply_writes(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        submission = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, submission)
        _correct_organization(submission)

        output = io.StringIO()
        call_command("refresh_diploma_snapshots", f"--competition={competition.id}", "--apply", stdout=output)

        assert DiplomaModel.objects.get(document_type="DIPLOMA").snapshot["organization"]["name"] == _SCHOOL
        assert "Перевыпущено: 1" in output.getvalue()

    def test_a_single_diploma_can_be_targeted_by_number(self, setup: tuple[CompetitionModel, CategoryModel]) -> None:
        competition, vocals = setup
        wanted = _submission(competition, vocals)
        other = _submission(competition, vocals)
        _assign(competition, vocals, _template("Диплом", "DIPLOMA"))
        _award(competition, vocals, wanted)
        _award(competition, vocals, other)
        _correct_organization(wanted)
        _correct_organization(other)
        number = DiplomaModel.objects.get(submission_id=wanted.id).number

        call_command("refresh_diploma_snapshots", f"--number={number}", "--apply", stdout=io.StringIO())

        assert DiplomaModel.objects.get(submission_id=wanted.id).snapshot["organization"]["name"] == _SCHOOL
        # Соседний диплом не тронут: точечный запуск — значит точечный.
        assert DiplomaModel.objects.get(submission_id=other.id).snapshot["organization"]["name"] is None

    def test_mass_apply_across_every_festival_is_refused(self) -> None:
        # За этим стоят чужие выданные документы — такое не должно запускаться одним
        # словом, по ошибке или из истории шелла.
        with pytest.raises(CommandError, match="--competition"):
            call_command("refresh_diploma_snapshots", "--apply", stdout=io.StringIO())
