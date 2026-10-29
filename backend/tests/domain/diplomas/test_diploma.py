"""Unit tests for the ``Diploma`` aggregate and its snapshot value objects.

Pure domain — no Django, no database.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from apps.diplomas.domain.entities import Diploma
from apps.diplomas.domain.value_objects import (
    AwardSnapshot,
    CompetitionSnapshot,
    DiplomaSnapshot,
    DiplomaStatus,
    MemberSnapshot,
    NominationSnapshot,
    OrganizationSnapshot,
    ParticipantSnapshot,
    PerformanceSnapshot,
    TeacherSnapshot,
)

_NOW = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
_LATER = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)


def _snapshot(*, degree: str | None = None) -> DiplomaSnapshot:
    return DiplomaSnapshot(
        participant=ParticipantSnapshot(display_name="Иванов Иван", age=12),
        teachers=(TeacherSnapshot(name="Петрова Мария", role="Педагог"),),
        organization=OrganizationSnapshot(name="ДШИ №1"),
        nomination=NominationSnapshot(title="Вокал", discipline="Эстрадный вокал"),
        performance=PerformanceSnapshot(title="Этюд"),
        competition=CompetitionSnapshot(title="Восходящие таланты", date="15.05.2026", city="Москва"),
        award=AwardSnapshot(degree=degree),
    )


def _create(snapshot: DiplomaSnapshot) -> Diploma:
    return Diploma.create(
        diploma_id=uuid.uuid4(),
        number="000001",
        verification_token="tok",
        competition_id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        template_id=uuid.uuid4(),
        snapshot=snapshot,
        now=_NOW,
    )


def test_created_diploma_is_draft_without_degree() -> None:
    diploma = _create(_snapshot(degree=None))

    assert diploma.status is DiplomaStatus.DRAFT
    assert diploma.degree is None
    assert diploma.print_pdf_path is None
    assert diploma.official_pdf_path is None
    assert diploma.issued_at is None
    assert diploma.version == 1


def test_snapshot_round_trips_through_dict() -> None:
    snapshot = _snapshot(degree="Лауреат I степени")

    restored = DiplomaSnapshot.from_dict(snapshot.to_dict())

    assert restored == snapshot


def test_award_degree_defaults_to_none() -> None:
    assert AwardSnapshot().degree is None
    assert DiplomaSnapshot.from_dict({"participant": {"display_name": "x"}}).award.degree is None


def test_with_degree_sets_only_the_degree_and_bumps_version() -> None:
    diploma = _create(_snapshot(degree=None))

    updated = diploma.with_degree("Гран-при", now=_NOW)

    assert updated.degree == "Гран-при"
    assert updated.version == 2
    # Everything else is frozen — the original is untouched.
    assert diploma.degree is None
    assert updated.number == diploma.number
    assert updated.snapshot.participant == diploma.snapshot.participant
    assert updated.snapshot.competition == diploma.snapshot.competition


class TestRefreshingASnapshot:
    """Пересборка снимка у уже существующего диплома.

    Единственное исключение из правила «выданный документ заморожен»: правка,
    сделанная организатором после генерации, должна доходить до бумаги. Проверяется
    то, чего это исключение не имеет права сломать, — тождество документа и то, что
    в снимке принадлежит не заявке.
    """

    def test_a_snapshot_that_has_not_moved_is_not_a_difference(self) -> None:
        diploma = _create(_snapshot(degree="Лауреат I степени"))

        # Пересобранный снимок всегда приходит без степени: она у жюри, а не в
        # заявке. Считать это расхождением значило бы перевыпускать весь реестр.
        assert diploma.differs_from(_snapshot(degree=None)) is False

    def test_a_corrected_organization_is_a_difference(self) -> None:
        diploma = _create(_snapshot())

        fresh = replace(_snapshot(), organization=OrganizationSnapshot(name="Гимназия №3"))

        assert diploma.differs_from(fresh) is True

    def test_refreshing_keeps_the_degree(self) -> None:
        # Самый дорогой способ ошибиться: пересобранный снимок несёт degree=None, и
        # прямая замена стёрла бы награды всему фестивалю.
        diploma = _create(_snapshot(degree="Гран-при"))

        updated = diploma.with_refreshed_snapshot(replace(_snapshot(), organization=OrganizationSnapshot(name="Гимназия №3")), now=_NOW)

        assert updated.degree == "Гран-при"
        assert updated.snapshot.organization.name == "Гимназия №3"

    def test_refreshing_keeps_the_member_of_an_individual_diploma(self) -> None:
        # Индивидуальный диплом — снимок коллектива, адресованный одному ребёнку.
        # Пересборка из заявки его не знает, и без переноса двенадцать дипломов
        # превратились бы в двенадцать копий ансамблевого.
        base = _create(_snapshot())
        individual = replace(base, snapshot=replace(base.snapshot, member=MemberSnapshot(full_name="Петров Пётр")), recipient="Петров Пётр")

        updated = individual.with_refreshed_snapshot(replace(_snapshot(), organization=OrganizationSnapshot(name="Гимназия №3")), now=_NOW)

        assert updated.snapshot.member == MemberSnapshot(full_name="Петров Пётр")
        assert updated.recipient == "Петров Пётр"

    def test_refreshing_keeps_what_the_document_is_identified_by(self) -> None:
        # Напечатанный QR ведёт на токен, бухгалтерия сверяется по номеру: перевыпуск
        # не имеет права сделать выданный диплом другим документом.
        diploma = _create(_snapshot()).issued("/media/official.pdf", now=_NOW)

        updated = diploma.with_refreshed_snapshot(replace(_snapshot(), organization=OrganizationSnapshot(name="Гимназия №3")), now=_LATER)

        assert updated.id == diploma.id
        assert updated.number == diploma.number
        assert updated.verification_token == diploma.verification_token
        assert updated.submission_id == diploma.submission_id
        assert updated.issued_at == diploma.issued_at
        assert updated.version == diploma.version + 1

    def test_the_original_is_untouched(self) -> None:
        diploma = _create(_snapshot())

        diploma.with_refreshed_snapshot(replace(_snapshot(), organization=OrganizationSnapshot(name="Гимназия №3")), now=_NOW)

        assert diploma.snapshot.organization.name == "ДШИ №1"


def test_printing_a_blank_does_not_un_issue_a_diploma() -> None:
    # Пересборка печатного пакета после публикации результатов — обычное дело
    # (добавили номинацию, поменяли макет). Выданный документ от этого выданным
    # быть не перестаёт.
    issued = _create(_snapshot(degree="Гран-при")).issued("/media/official.pdf", now=_NOW)

    reprinted = issued.with_print_pdf("/media/print.pdf", now=_LATER)

    assert reprinted.status is DiplomaStatus.ISSUED
    assert reprinted.official_pdf_path == "/media/official.pdf"
    assert reprinted.print_pdf_path == "/media/print.pdf"


def test_printing_a_blank_marks_an_unissued_diploma_generated() -> None:
    diploma = _create(_snapshot())

    assert diploma.with_print_pdf("/media/print.pdf", now=_NOW).status is DiplomaStatus.GENERATED
