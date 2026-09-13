"""Кем подписана заявка в очереди организатора.

Карточка очереди печатала ``applicant_id`` — голый UUID, по которому нельзя ни
узнать коллектив, ни сопоставить перевод, ни позвонить. Здесь закреплено, что в
строке стоит тот, кто выступает, а идентификатор пользователя туда не возвращается.
"""

from __future__ import annotations

from apps.applications.presentation.api.v1.organizer.views import _applicant_label


def test_solo_is_named_last_first_middle() -> None:
    participants = [{"last_name": "Иванова", "first_name": "Мария", "middle_name": "Петровна"}]
    assert _applicant_label(participants) == "Иванова Мария Петровна"


def test_a_collective_is_named_by_its_caption() -> None:
    """У коллектива нет ФИО — только название, под которым он и заявлен."""
    assert _applicant_label([{"display_name": "Ансамбль «Радуга»", "member_count": 12}]) == "Ансамбль «Радуга»"


def test_several_performers_are_counted_rather_than_listed() -> None:
    """Строка в списке одна: развёрнутый состав читают в рабочей карточке."""
    participants = [
        {"last_name": "Иванова", "first_name": "Мария"},
        {"last_name": "Петров", "first_name": "Пётр"},
        {"display_name": "Дуэт «Эхо»"},
    ]
    assert _applicant_label(participants) == "Иванова Мария и ещё 2"


def test_an_entry_without_performers_falls_back_to_the_studio() -> None:
    assert _applicant_label([], "Студия «Вдохновение»", "Сидоров Сидор") == "Студия «Вдохновение»"


def test_blank_fallbacks_are_skipped_in_order() -> None:
    assert _applicant_label([], "", "   ", "Сидоров Сидор") == "Сидоров Сидор"


def test_nothing_to_name_reads_as_a_dash_rather_than_an_identifier() -> None:
    assert _applicant_label([], None, "") == "—"


def test_a_participant_row_with_only_blanks_does_not_win_over_the_studio() -> None:
    """Пустая запись участника раньше давала пустую строку в карточке."""
    assert _applicant_label([{"display_name": "  ", "last_name": ""}], "Студия «Вдохновение»") == "Студия «Вдохновение»"
