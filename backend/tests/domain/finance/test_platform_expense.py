"""Правила, на которых держится запись о расходе, — без базы и без HTTP.

Здесь закреплено то, что не должно зависеть от того, какой край спросил: расход
без назначения не собирается вообще, сумма всегда положительная и с копейками,
«1 200,50» — это обычная запись числа, а перевод траты с клиента на платформу
отличается от «не трогай это поле».
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from apps.finance.domain.entities import PlatformExpense
from apps.finance.domain.exceptions import InvalidExpenseDataError
from apps.finance.domain.value_objects import ExpenseAmount, ExpenseCategory, ExpenseNote, ExpensePurpose

_NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
_DAY = date(2026, 3, 1)


def _expense(**overrides: object) -> PlatformExpense:
    """Записанный расход со всем обязательным и без лишнего."""
    fields: dict[str, object] = {
        "expense_id": uuid.uuid4(),
        "amount": ExpenseAmount(Decimal("100.00")),
        "category": ExpenseCategory.INFRASTRUCTURE,
        "purpose": ExpensePurpose("Хостинг за март"),
        "spent_at": _DAY,
        "now": _NOW,
    }
    fields.update(overrides)
    return PlatformExpense.record(**fields)  # type: ignore[arg-type]


class TestСумма:
    def test_округляется_до_копеек(self) -> None:
        assert ExpenseAmount(Decimal("10.005")).value == Decimal("10.01")

    def test_ноль_и_минус_это_не_расход(self) -> None:
        for value in (Decimal("0"), Decimal("-1.00")):
            with pytest.raises(InvalidExpenseDataError):
                ExpenseAmount(value)

    def test_читает_запятую_и_пробелы_как_обычную_запись_числа(self) -> None:
        # Так пишут в счетах и так набирают с клавиатуры; отказать здесь значит
        # отказать обычному написанию суммы.
        assert ExpenseAmount.parse("1 200,50").value == Decimal("1200.50")

    def test_отказывает_тому_что_не_число(self) -> None:
        with pytest.raises(InvalidExpenseDataError):
            ExpenseAmount.parse("сколько-то")

    def test_отказывает_сумме_с_лишними_нулями(self) -> None:
        with pytest.raises(InvalidExpenseDataError):
            ExpenseAmount.parse("999999999999")


class TestНазначение:
    def test_пустое_назначение_не_проходит(self) -> None:
        # Сумма без строки «за что» — это число, которое можно сложить и нельзя
        # объяснить, а объяснение итога и есть смысл этой книги.
        with pytest.raises(InvalidExpenseDataError):
            ExpensePurpose("   ")

    def test_комментарий_может_быть_пустым(self) -> None:
        assert ExpenseNote().empty


class TestСтатья:
    def test_читает_известную_статью(self) -> None:
        assert ExpenseCategory.parse("marketing") is ExpenseCategory.MARKETING

    def test_отказывает_выдуманной(self) -> None:
        with pytest.raises(InvalidExpenseDataError):
            ExpenseCategory.parse("ВЫДУМАННАЯ")


class TestЗапись:
    def test_расход_без_организации_это_расход_платформы(self) -> None:
        expense = _expense()

        assert expense.organization_id is None
        assert expense.version == 1
        assert expense.persisted_version is None

    def test_собирается_только_через_фабрику(self) -> None:
        with pytest.raises(InvalidExpenseDataError):
            PlatformExpense(
                _token=object(),
                _id=uuid.uuid4(),
                _amount=ExpenseAmount(Decimal("1.00")),
                _category=ExpenseCategory.OTHER,
                _purpose=ExpensePurpose("Что-то"),
                _spent_at=_DAY,
                _created_at=_NOW,
                _updated_at=_NOW,
            )


class TestИсправление:
    def test_меняет_только_переданное(self) -> None:
        expense = _expense()

        expense.amend(now=_NOW, amount=ExpenseAmount(Decimal("55.00")))

        assert expense.amount.value == Decimal("55.00")
        assert expense.purpose.value == "Хостинг за март"
        assert expense.version == 2

    def test_переводит_трату_на_платформу_только_по_явной_просьбе(self) -> None:
        organization = uuid.uuid4()
        expense = _expense(organization_id=organization)

        # Без reassign None значит «не трогай»: иначе любое исправление суммы
        # молча снимало бы трату с клиента.
        expense.amend(now=_NOW, purpose=ExpensePurpose("Печать дипломов"))
        assert expense.organization_id == organization

        expense.amend(now=_NOW, organization=None, reassign=True)
        assert expense.organization_id is None
