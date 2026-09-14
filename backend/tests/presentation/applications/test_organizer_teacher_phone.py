"""Телефон педагога в рабочей карточке организатора.

Карточка печатала педагога именем и ролью — этого хватает, пока с заявкой всё в
порядке. Когда с ней что-то не так (не та фонограмма, сорванный хронометраж,
непонятный возрастной состав), звонить надо не участнику, а тому, кто его готовил,
и организатор уходил искать номер в переписке. Телефон лежит в справочнике педагогов
кабинета, а на заявке от педагога остаётся только ссылка на карточку справочника —
здесь закреплено, что она разворачивается в номер, и что у вписанного руками
педагога номера честно нет.
"""

from __future__ import annotations

import pytest
from pytest_django.fixtures import DjangoAssertNumQueries

from apps.applications.application.dto import TeacherView
from apps.applications.presentation.api.v1.organizer.views import _directory_phones, _teacher_card
from apps.teachers.infrastructure.models import TeacherModel, uuid7

pytestmark = pytest.mark.django_db


def _teacher(*, directory_teacher_id: str | None) -> TeacherView:
    return TeacherView(
        id=str(uuid7()),
        first_name="Ольга",
        last_name="Петрова",
        middle_name=None,
        role="TEACHER",
        directory_teacher_id=directory_teacher_id,
    )


def _directory_row(*, phone: str | None) -> TeacherModel:
    return TeacherModel.objects.create(
        owner_id=uuid7(),
        first_name="Ольга",
        last_name="Петрова",
        role="TEACHER",
        status="ACTIVE",
        phone=phone,
    )


def test_the_number_comes_from_the_cabinet_directory() -> None:
    row = _directory_row(phone="+375 29 123-45-67")
    teacher = _teacher(directory_teacher_id=str(row.id))

    card = _teacher_card(teacher, _directory_phones([teacher]))

    assert card["name"] == "Петрова Ольга"
    assert card["phone"] == "+375 29 123-45-67"


def test_a_teacher_typed_by_hand_has_nowhere_to_call() -> None:
    """Без ссылки на справочник номера нет — пустое поле честнее выдуманного."""
    teacher = _teacher(directory_teacher_id=None)

    assert _teacher_card(teacher, _directory_phones([teacher]))["phone"] is None


def test_a_directory_card_without_a_number_does_not_print_an_empty_one() -> None:
    row = _directory_row(phone="   ")
    teacher = _teacher(directory_teacher_id=str(row.id))

    assert _teacher_card(teacher, _directory_phones([teacher]))["phone"] is None


def test_a_deleted_directory_card_stops_answering() -> None:
    """Справочник — источник правды: удалённую карточку карточка заявки не воскрешает."""
    row = _directory_row(phone="+375 29 123-45-67")
    TeacherModel.objects.filter(pk=row.id).update(deleted_at="2026-09-14T00:00:00Z")
    teacher = _teacher(directory_teacher_id=str(row.id))

    assert _teacher_card(teacher, _directory_phones([teacher]))["phone"] is None


def test_the_whole_application_costs_one_query_to_the_directory(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    """Номеров столько же, сколько педагогов, а запрос один: карточка открывается на
    каждое переключение в очереди."""
    rows = [_directory_row(phone=f"+37529000000{index}") for index in range(3)]
    teachers = [_teacher(directory_teacher_id=str(row.id)) for row in rows]

    with django_assert_num_queries(1):
        phones = _directory_phones(teachers)

    assert [_teacher_card(t, phones)["phone"] for t in teachers] == ["+375290000000", "+375290000001", "+375290000002"]


def test_no_directory_teachers_at_all_asks_the_database_nothing(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    with django_assert_num_queries(0):
        assert _directory_phones([_teacher(directory_teacher_id=None)]) == {}
