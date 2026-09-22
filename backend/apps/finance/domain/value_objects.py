"""Value objects for the Finance bounded context.

Immutable, identity-less concepts (DATA-001 §8), framework-free.

Everything here serves one record: a sum the platform spent, and the line saying
what it was spent on. The money is a :class:`decimal.Decimal` and never a float —
these figures are subtracted from the commission the operator invoices, and a
rounding error in a profit figure is a wrong answer to the only question the
screen exists to answer.

Identifiers stay plain :class:`uuid.UUID` values, as in Reviews: this context
holds its own ids and references outward by id alone (``organization_id``).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Final

from .exceptions import InvalidExpenseDataError

__all__ = [
    "EXPENSE_NOTE_MAX",
    "EXPENSE_PURPOSE_MAX",
    "ExpenseAmount",
    "ExpenseCategory",
    "ExpenseNote",
    "ExpensePurpose",
]

#: The line that says what the money went on — the one thing an expense may not be
#: without. Short on purpose: it is a row in a table, not a memo.
EXPENSE_PURPOSE_MAX: Final = 200

#: Room for the detail that did not fit on the line: an invoice number, who was
#: paid, why this month's figure is not last month's. Optional, and usually empty.
EXPENSE_NOTE_MAX: Final = 2000

#: Two decimal places, like every other money figure on the platform.
_MONEY_QUANTUM: Final = Decimal("0.01")

#: A ceiling high enough that no real expense reaches it and low enough that a
#: mistyped figure — an amount pasted with its thousands separators intact — is
#: refused at the form rather than discovered in a profit total.
_AMOUNT_MAX: Final = Decimal("100000000")


class ExpenseCategory(StrEnum):
    """What kind of cost this is — the grouping the operator reads totals by.

    A closed list rather than free text, because the whole point of the category is
    that two rows written six months apart land in the same bucket. The free text
    lives beside it in :class:`ExpensePurpose`, which is where the specifics go.

    ``OTHER`` is deliberate and not a gap: an expense nobody anticipated must be
    recordable the day it happens, not after the enum ships a new member.
    """

    INFRASTRUCTURE = "INFRASTRUCTURE"
    MARKETING = "MARKETING"
    PAYROLL = "PAYROLL"
    CONTRACTORS = "CONTRACTORS"
    EQUIPMENT = "EQUIPMENT"
    EVENT = "EVENT"
    BANK = "BANK"
    TAX = "TAX"
    OTHER = "OTHER"

    @classmethod
    def parse(cls, value: str) -> ExpenseCategory:
        """The category named by ``value``, refusing anything not on the list."""
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            raise InvalidExpenseDataError("Неизвестная статья расхода.") from exc


@dataclass(frozen=True, slots=True)
class ExpenseAmount:
    """A sum the platform spent, always positive and always to the kopeck.

    Positive rather than signed: this ledger records costs, and the sign lives in
    the arithmetic that subtracts it. An expense of zero is refused too — it is
    either a mistake or a note, and there is a field for notes.
    """

    value: Decimal

    def __post_init__(self) -> None:
        try:
            amount = Decimal(str(self.value)).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvalidExpenseDataError("Сумма расхода должна быть числом.") from exc
        if amount <= 0:
            raise InvalidExpenseDataError("Сумма расхода должна быть больше нуля.")
        if amount > _AMOUNT_MAX:
            raise InvalidExpenseDataError("Слишком большая сумма — проверьте, не лишние ли это нули.")
        object.__setattr__(self, "value", amount)

    @classmethod
    def parse(cls, value: str) -> ExpenseAmount:
        """Build an amount from what somebody typed.

        A comma is a decimal point here: Russian keyboards and Russian invoices both
        write "1200,50", and refusing that would be refusing the ordinary spelling.
        Spaces go too — a figure pasted out of a spreadsheet arrives grouped.
        """
        cleaned = str(value).replace("\u00a0", "").replace(" ", "").replace(",", ".").strip()
        if not cleaned:
            raise InvalidExpenseDataError("Укажите сумму расхода.")
        try:
            return cls(Decimal(cleaned))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvalidExpenseDataError("Сумма расхода должна быть числом.") from exc

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ExpensePurpose:
    """What the money was spent on, in the operator's own words.

    Required, because an expense whose purpose nobody wrote down is a number that
    can be totalled and not explained — and explaining the total is the whole
    reason this ledger exists rather than a single figure typed each month.
    """

    value: str

    def __post_init__(self) -> None:
        text = " ".join(str(self.value).split()).strip()
        if not text:
            raise InvalidExpenseDataError("Напишите, за что расход — без этого он не сохраняется.")
        if len(text) > EXPENSE_PURPOSE_MAX:
            raise InvalidExpenseDataError(f"Назначение расхода — не длиннее {EXPENSE_PURPOSE_MAX} символов.")
        object.__setattr__(self, "value", text)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ExpenseNote:
    """The detail under the line: an invoice number, a contractor, a caveat.

    Blank is the ordinary case and not an error. Newlines survive — somebody
    listing three invoices puts each on its own line.
    """

    value: str = ""

    def __post_init__(self) -> None:
        lines = [" ".join(line.split()) for line in str(self.value).splitlines()]
        text = "\n".join(lines).strip()
        if len(text) > EXPENSE_NOTE_MAX:
            raise InvalidExpenseDataError(f"Комментарий — не длиннее {EXPENSE_NOTE_MAX} символов.")
        object.__setattr__(self, "value", text)

    @property
    def empty(self) -> bool:
        return not self.value

    def __str__(self) -> str:
        return self.value
