"""Правила записи о поступившей комиссии — без базы и без HTTP.

Здесь закреплено то, что отличает поступление от расхода, и ровно поэтому это
отдельный агрегат, а не расход со знаком минус: у поступления всегда есть
плательщик, у расхода его может не быть вовсе. Остальное — обычная бухгалтерия
оператора: сумма положительная и с копейками, «1 200,50» это обычная запись
числа, опечатку можно исправить.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from apps.finance.domain.entities import CommissionPayment
from apps.finance.domain.exceptions import InvalidCommissionPaymentDataError
from apps.finance.domain.value_objects import PaymentAmount, PaymentNote

_NOW = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)
_DAY = date(2026, 3, 20)


def _payment(**overrides: object) -> CommissionPayment:
    """Записанное поступление со всем обязательным и без лишнего."""
    fields: dict[str, object] = {
        "payment_id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "amount": PaymentAmount(Decimal("100.00")),
        "received_at": _DAY,
        "now": _NOW,
    }
    fields.update(overrides)
    return CommissionPayment.record(**fields)  # type: ignore[arg-type]


class TestСумма:
    def test_округляется_до_копеек(self) -> None:
        assert PaymentAmount(Decimal("10.005")).value == Decimal("10.01")

    def test_ноль_и_минус_это_не_поступление(self) -> None:
        # Деньги в обратную сторону — это расход, и у него своя книга.
        for value in (Decimal("0"), Decimal("-1.00")):
            with pytest.raises(InvalidCommissionPaymentDataError):
                PaymentAmount(value)

    def test_читает_запятую_и_пробелы_как_обычную_запись_числа(self) -> None:
        # Сумму списывают с платёжного поручения, где написано именно так.
        assert PaymentAmount.parse("1 200,50").value == Decimal("1200.50")

    def test_отказывает_тому_что_не_число(self) -> None:
        with pytest.raises(InvalidCommissionPaymentDataError):
            PaymentAmount.parse("сколько-то")

    def test_отказывает_сумме_с_лишними_нулями(self) -> None:
        with pytest.raises(InvalidCommissionPaymentDataError):
            PaymentAmount.parse("999999999999")


class TestПлательщик:
    def test_поступление_без_организации_не_собирается(self) -> None:
        # Главное отличие от расхода: расход платформа может нести сама, а
        # поступление, которое никому не уменьшает долг, — это не поступление.
        with pytest.raises(InvalidCommissionPaymentDataError):
            _payment(organization_id=None)

    def test_организация_это_идентификатор_а_не_название(self) -> None:
        with pytest.raises(InvalidCommissionPaymentDataError):
            _payment(organization_id="Гармония")


class TestЗаписьИИсправление:
    def test_собирается_только_через_фабрику(self) -> None:
        with pytest.raises(InvalidCommissionPaymentDataError):
            CommissionPayment(
                _token=object(),
                _id=uuid.uuid4(),
                _organization_id=uuid.uuid4(),
                _amount=PaymentAmount(Decimal("1.00")),
                _received_at=_DAY,
                _created_at=_NOW,
                _updated_at=_NOW,
            )

    def test_без_комментария_это_обычный_случай(self) -> None:
        assert _payment().note.empty

    def test_исправление_суммы_поднимает_версию(self) -> None:
        payment = _payment()
        later = datetime(2026, 3, 21, 9, 0, tzinfo=UTC)

        payment.amend(now=later, amount=PaymentAmount(Decimal("150.00")))

        assert payment.amount.value == Decimal("150.00")
        assert payment.version == 2
        assert payment.updated_at == later

    def test_пропущенные_поля_остаются_как_были(self) -> None:
        payment = _payment(note=PaymentNote("п/п 114"))

        payment.amend(now=_NOW, amount=PaymentAmount(Decimal("150.00")))

        assert payment.note.value == "п/п 114"
        assert payment.received_at == _DAY

    def test_платёж_можно_перевести_на_другую_организацию(self) -> None:
        # Деньги, зачисленные не тому клиенту, — обычная правка, а не новая запись.
        payment = _payment()
        another = uuid.uuid4()

        payment.amend(now=_NOW, organization_id=another)

        assert payment.organization_id == another

    def test_не_указанная_организация_означает_не_трогай(self) -> None:
        # У расхода тут нужен флаг reassign, потому что None там — это значение
        # («неси сам»). Здесь такого значения нет, и флаг был бы лишним.
        payment = _payment()
        payer = payment.organization_id

        payment.amend(now=_NOW, amount=PaymentAmount(Decimal("2.00")))

        assert payment.organization_id == payer


class TestВосстановлениеИзБазы:
    def test_не_перепроверяет_правила_и_помнит_версию(self) -> None:
        payment_id = uuid.uuid4()
        organization_id = uuid.uuid4()

        payment = CommissionPayment.rehydrate(
            payment_id=payment_id,
            organization_id=organization_id,
            amount=PaymentAmount(Decimal("40.00")),
            received_at=_DAY,
            created_at=_NOW,
            updated_at=_NOW,
            note=PaymentNote("п/п 114"),
            version=3,
        )

        assert payment.id == payment_id
        assert payment.organization_id == organization_id
        assert payment.version == 3
        # Прочитан на третьей версии — на неё и опирается запись обратно.
        assert payment.persisted_version == 3

    def test_отметка_о_записи_догоняет_текущую_версию(self) -> None:
        payment = _payment()
        payment.amend(now=_NOW, amount=PaymentAmount(Decimal("5.00")))

        payment.mark_persisted()

        assert payment.persisted_version == payment.version


class TestКомментарий:
    def test_пустой_это_норма(self) -> None:
        assert PaymentNote().empty

    def test_переносы_строк_сохраняются(self) -> None:
        # Два платёжных поручения одной суммой — каждое на своей строке.
        assert PaymentNote("п/п 114\nп/п 115").value == "п/п 114\nп/п 115"

    def test_слишком_длинный_отказывается(self) -> None:
        with pytest.raises(InvalidCommissionPaymentDataError):
            PaymentNote("я" * 2001)
