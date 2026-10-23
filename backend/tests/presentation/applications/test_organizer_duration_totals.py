"""Хронометраж номера, из которого складывается итог по жанру.

Фильтр по жанру в консоли организатора показывает не только число заявок, но и
общее время выступлений — по нему верстают блок в расписании. Значение приходит
из JSON заявки, то есть из данных произвольной давности, и одна испорченная
запись не должна ни обнулить итог, ни уронить запрос.
"""

from __future__ import annotations

import pytest

from apps.applications.presentation.api.v1.organizer.support import _duration_seconds


def test_a_normal_duration_comes_through_unchanged() -> None:
    assert _duration_seconds(150) == 150


def test_a_duration_stored_as_text_is_still_counted() -> None:
    """Старые записи хранят число строкой; терять их время незачем."""
    assert _duration_seconds("150") == 150


@pytest.mark.parametrize("value", [None, "", "три минуты", {}, []])
def test_anything_that_is_not_a_number_counts_as_nothing(value: object) -> None:
    assert _duration_seconds(value) == 0


def test_a_negative_duration_does_not_eat_someone_else_s_time() -> None:
    """Иначе одна кривая запись уменьшила бы итог по всему жанру."""
    assert _duration_seconds(-90) == 0


def test_a_fractional_duration_is_truncated_rather_than_dropped() -> None:
    assert _duration_seconds(150.9) == 150
