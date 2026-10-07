"""Как далеко достаёт правка содержимого заявки — и где она останавливается.

Окно одно на всех. Домен спрашивает только «есть ли ещё что править»: номер жив,
пока он не состоялся и не отменён. Кто и до какого числа вправе его трогать —
вопрос календаря, а календарь живёт в сценариях: заявителю правку закрывает срок
приёма заявок, организатор его сознательно не проверяет. Пока приём открыт,
заявитель правит свой номер сам — хоть одобренный, хоть уже стоящий в расписании:
фамилию с заявки печатают на дипломе, и починить опечатку должен тот, кто её
сделал, а не переписка с организатором.

Проверяется само правило, а не use case: домен — единственный, кто решает, можно
ли сейчас менять номер, и остальные слои только передают ему вопрос.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from apps.applications.domain.entities import Submission
from apps.applications.domain.exceptions import PriceSnapshotLockedError, SubmissionNotEditableError
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    BirthDate,
    CompetitionId,
    DisciplineId,
    Duration,
    Gender,
    Money,
    NominationId,
    ParticipantCountRange,
    ParticipantGroupId,
    ParticipantId,
    ParticipationFormatId,
    Performance,
    PerformanceTitle,
    PersonName,
    PriceSnapshot,
    SubmissionId,
    SubmissionParticipationPolicy,
    SubmissionStatus,
    TeacherId,
    TeacherRole,
    UserId,
)

NOW = datetime(2026, 7, 10, tzinfo=UTC)


def _new_id() -> uuid.UUID:
    return SubmissionId.generate().value


def _performance(title: str = "Лебединое озеро") -> Performance:
    return Performance(
        title=PerformanceTitle(title),
        duration=Duration.of(minutes=3, seconds=30),
        nomination_id=NominationId.from_uuid(_new_id()),
        discipline_id=DisciplineId.from_uuid(_new_id()),
        age_category_id=AgeCategoryId.from_uuid(_new_id()),
        participant_group_id=ParticipantGroupId.from_uuid(_new_id()),
        participation_format_id=ParticipationFormatId.from_uuid(_new_id()),
    )


def _walked_to(status: SubmissionStatus) -> Submission:
    """Заявка, доведённая по обычному пути до `status`."""
    submission, _ = Submission.draft(
        submission_id=SubmissionId.generate(),
        competition_id=CompetitionId.from_uuid(_new_id()),
        applicant_id=UserId.from_uuid(_new_id()),
        now=NOW,
    )
    submission.set_performance(performance=_performance(), now=NOW)
    submission.add_participant(
        participant_id=ParticipantId.generate(),
        name=PersonName(first_name="Анна", last_name="Иванова"),
        birth_date=BirthDate(date(2012, 5, 1)),
        gender=Gender.FEMALE,
        now=NOW,
    )
    submission.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("1500"), calculated_at=NOW), now=NOW)
    if status is SubmissionStatus.DRAFT:
        return submission
    submission.submit(policy=SubmissionParticipationPolicy(participant_count_range=ParticipantCountRange(1, 1)), now=NOW)
    for step, target in (
        (submission.begin_review, SubmissionStatus.UNDER_REVIEW),
        (submission.approve, SubmissionStatus.APPROVED),
        (submission.await_payment, SubmissionStatus.WAITING_PAYMENT),
        (submission.mark_paid, SubmissionStatus.PAID),
        (submission.accept, SubmissionStatus.ACCEPTED),
        (submission.schedule, SubmissionStatus.SCHEDULED),
        (submission.complete, SubmissionStatus.COMPLETED),
    ):
        if submission.status is status:
            break
        step(now=NOW)
        if target is status:
            break
    return submission


#: Статусы, в которых заявитель уже не правит номер сам: взнос оплачен, номер стоит
#: в программе. До них правка остаётся за заявителем — её закрывает срок приёма
#: заявок, а не решение организатора.
#: Весь живой путь номера — везде содержимое правится.
_LIVE = [
    SubmissionStatus.DRAFT,
    SubmissionStatus.SUBMITTED,
    SubmissionStatus.UNDER_REVIEW,
    SubmissionStatus.APPROVED,
    SubmissionStatus.WAITING_PAYMENT,
    SubmissionStatus.PAID,
    SubmissionStatus.ACCEPTED,
    SubmissionStatus.SCHEDULED,
]


class TestTheWindow:
    @pytest.mark.parametrize("status", _LIVE)
    def test_the_entry_stays_editable_while_it_is_live(self, status: SubmissionStatus) -> None:
        """Ни одобрение, ни счёт, ни место в программе не делают опечатку верной."""
        submission = _walked_to(status)
        assert submission.status is status

        submission.set_performance(performance=_performance("Лебединое озеро (фрагмент)"), now=NOW)

        assert submission.performance is not None
        assert submission.performance.title.value == "Лебединое озеро (фрагмент)"

    def test_a_performer_can_be_replaced_on_a_scheduled_entry(self) -> None:
        # Фамилия с заявки печатается на дипломе — исправить её надо до фестиваля,
        # а не после.
        submission = _walked_to(SubmissionStatus.SCHEDULED)
        wrong = submission.participants[0]

        submission.remove_participant(participant_id=wrong.id, now=NOW)
        submission.add_participant(
            participant_id=ParticipantId.generate(),
            name=PersonName(first_name="Анна", last_name="Иванова", middle_name="Петровна"),
            birth_date=BirthDate(date(2012, 5, 1)),
            gender=Gender.FEMALE,
            now=NOW,
        )

        assert [p.display_name for p in submission.participants] == ["Иванова Анна Петровна"]

    def test_a_teacher_can_be_credited_on_an_accepted_entry(self) -> None:
        submission = _walked_to(SubmissionStatus.ACCEPTED)

        submission.add_teacher(
            teacher_id=TeacherId.generate(),
            name=PersonName(first_name="Ольга", last_name="Петрова"),
            role=TeacherRole("Педагог"),
            now=NOW,
        )

        assert [t.name.full_name for t in submission.teachers] == ["Петрова Ольга"]


class TestWhereItStops:
    def test_a_performed_entry_is_closed(self) -> None:
        """Выступление состоялось — правка переписывала бы то, что уже случилось,
        и то, что могло уйти в реестр дипломов."""
        submission = _walked_to(SubmissionStatus.COMPLETED)

        with pytest.raises(SubmissionNotEditableError):
            submission.set_performance(performance=_performance("Задним числом"), now=NOW)

    def test_a_cancelled_entry_is_closed(self) -> None:
        submission = _walked_to(SubmissionStatus.SUBMITTED)
        submission.cancel(now=NOW)

        with pytest.raises(SubmissionNotEditableError):
            submission.remove_participant(participant_id=submission.participants[0].id, now=NOW)

    @pytest.mark.parametrize("status", _LIVE)
    def test_the_predicate_agrees_with_what_the_methods_do(self, status: SubmissionStatus) -> None:
        # Карточка организатора показывает кнопку по этому предикату; если он
        # разойдётся с методами, кнопка будет обещать невозможное.
        assert _walked_to(status).is_editable() is True

    def test_the_predicate_closes_where_the_lifecycle_ends(self) -> None:
        assert _walked_to(SubmissionStatus.COMPLETED).is_editable() is False


class TestThePriceIsNotTouched:
    def test_correcting_the_entry_leaves_the_frozen_price_alone(self) -> None:
        """Цена — то, что участнику назвали и что он оплатил. Правка фамилии не
        повод пересчитать счёт."""
        submission = _walked_to(SubmissionStatus.PAID)
        before = submission.price_snapshot

        submission.set_performance(performance=_performance("Новое название"), now=NOW)

        assert submission.price_snapshot == before

    def test_the_snapshot_itself_is_sealed_once_the_order_is_invoiced(self) -> None:
        """Содержимое живёт дольше цены: счёт выставлен — сумма перестала двигаться."""
        submission = _walked_to(SubmissionStatus.WAITING_PAYMENT)

        with pytest.raises(PriceSnapshotLockedError):
            submission.set_price_snapshot(price_snapshot=PriceSnapshot(price=Money.of("1"), calculated_at=NOW), now=NOW)
