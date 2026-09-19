"""Учреждение в рабочей карточке организатора.

Карточка называла фестиваль, номера, статус и заказчика — но не учреждение, от
которого заявка пришла. Очередь же разбирают именно школами: одна присылает десяток
номеров, и сверять оплату, звонить и собирать программу удобнее по учреждению, а не
по каждому участнику отдельно.

Имя берётся со снимка на самой заявке, а не из справочника кабинета: учреждение там
могли переименовать или удалить, а в заявке оно должно остаться таким, каким его
выбирали. Подать заявку можно и не от учреждения — тогда строки на карточке нет.
"""

from __future__ import annotations

from apps.applications.presentation.api.v1.organizer.views import _educational_organization_name


def test_the_card_names_the_institution_the_entry_came_from() -> None:
    row = {"organization_name": "ДШИ № 5"}

    assert _educational_organization_name(row) == "ДШИ № 5"


def test_an_entry_sent_privately_has_no_institution_line() -> None:
    """Не у всякой заявки есть учреждение, и пустая строка честнее выдуманной."""
    assert _educational_organization_name({"organization_name": None}) is None


def test_a_blank_snapshot_does_not_print_an_empty_line() -> None:
    assert _educational_organization_name({"organization_name": "   "}) is None


def test_the_name_is_read_as_it_was_chosen() -> None:
    """Снимок с заявки, а не справочник: переименование школы не переписывает заявку."""
    row = {"organization_name": "  Детская школа искусств «Взлёт»  "}

    assert _educational_organization_name(row) == "Детская школа искусств «Взлёт»"
