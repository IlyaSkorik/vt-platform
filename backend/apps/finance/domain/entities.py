"""The Finance context's one aggregate: a sum the platform spent.

:class:`PlatformExpense` is the other half of the operator's books. The commission
side is already known — it is derived from the orders organizations take, and
nobody types it in. What the platform *spends* has no such source: hosting, a
contractor, an advertisement, a bank fee. It is entered by hand, and this is the
record of one such entry.

Three decisions shape it.

**An expense may name an organization, or name none.** A cost incurred for one
client belongs against that client's commission, which is what makes "are we in
the black on this one?" answerable. A server bill belongs to the platform and to
no client, and forcing it onto one would quietly libel that organization's line.
So ``organization_id`` is optional, and an expense without one is a platform cost
rather than an unassigned one.

**The purpose is not optional.** A ledger of sums without the line saying what
each was for is a number that can be totalled and never explained.

**It is correctable, not immutable.** Unlike a review — somebody else's words —
this is the operator's own bookkeeping, and a typo in an amount is a wrong profit
figure until it is fixed. :meth:`amend` is that fix; removal is the repository's
soft delete, so a correction never destroys what the books said before.

Framework-free (no Django, no DRF, no clock, no IO): time always arrives as ``now``.
"""

from __future__ import annotations

import uuid
from dataclasses import InitVar, dataclass
from datetime import date, datetime
from typing import Final

from .exceptions import InvalidExpenseDataError
from .value_objects import ExpenseAmount, ExpenseCategory, ExpenseNote, ExpensePurpose

__all__ = ["PlatformExpense"]

#: Opaque capability token proving construction went through a factory.
_CREATION_TOKEN: Final = object()


@dataclass(slots=True, eq=False, repr=False)
class PlatformExpense:
    """One cost the platform carried, with the line saying what it was for.

    ``spent_at`` is a :class:`datetime.date` and not an instant: an expense happens
    on a day, the invoice says which day, and the hour it was typed into the
    console is a different fact — that one is ``created_at`` on the row.
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _amount: ExpenseAmount
    _category: ExpenseCategory
    _purpose: ExpensePurpose
    _spent_at: date
    _created_at: datetime
    _updated_at: datetime
    #: The organization this cost was carried for, when it was carried for one.
    #: ``None`` is a platform-wide cost and the ordinary case for infrastructure.
    _organization_id: uuid.UUID | None = None
    _note: ExpenseNote | None = None
    #: Which operator recorded it. Kept as a bare id: this context has no business
    #: knowing what people are called, and the console resolves the name it shows.
    _recorded_by: uuid.UUID | None = None
    _version: int = 1
    #: The version this aggregate was last read at, or ``None`` for one never stored.
    _persisted_version: int | None = None

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise InvalidExpenseDataError("PlatformExpense must be created via record() or rehydrate().")
        if self._note is None:
            self._note = ExpenseNote()

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def record(
        cls,
        *,
        expense_id: uuid.UUID,
        amount: ExpenseAmount,
        category: ExpenseCategory,
        purpose: ExpensePurpose,
        spent_at: date,
        now: datetime,
        organization_id: uuid.UUID | None = None,
        note: ExpenseNote | None = None,
        recorded_by: uuid.UUID | None = None,
    ) -> PlatformExpense:
        """Enter a cost into the books."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=expense_id,
            _amount=amount,
            _category=category,
            _purpose=purpose,
            _spent_at=spent_at,
            _created_at=now,
            _updated_at=now,
            _organization_id=organization_id,
            _note=note or ExpenseNote(),
            _recorded_by=recorded_by,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        expense_id: uuid.UUID,
        amount: ExpenseAmount,
        category: ExpenseCategory,
        purpose: ExpensePurpose,
        spent_at: date,
        created_at: datetime,
        updated_at: datetime,
        organization_id: uuid.UUID | None = None,
        note: ExpenseNote | None = None,
        recorded_by: uuid.UUID | None = None,
        version: int = 1,
    ) -> PlatformExpense:
        """Rebuild a stored expense without re-running its creation rules."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=expense_id,
            _amount=amount,
            _category=category,
            _purpose=purpose,
            _spent_at=spent_at,
            _created_at=created_at,
            _updated_at=updated_at,
            _organization_id=organization_id,
            _note=note or ExpenseNote(),
            _recorded_by=recorded_by,
            _version=version,
            _persisted_version=version,
        )

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def amend(
        self,
        *,
        now: datetime,
        amount: ExpenseAmount | None = None,
        category: ExpenseCategory | None = None,
        purpose: ExpensePurpose | None = None,
        spent_at: date | None = None,
        note: ExpenseNote | None = None,
        organization: uuid.UUID | None = None,
        reassign: bool = False,
    ) -> None:
        """Correct a recorded expense. ``None`` everywhere means "leave as it was".

        ``organization`` is the one field where ``None`` is also a *value* — moving
        a cost off a client and onto the platform is an ordinary correction. So it
        takes ``reassign`` to say the field was meant at all, rather than inventing
        a sentinel that every caller would have to import.
        """
        if amount is not None:
            self._amount = amount
        if category is not None:
            self._category = category
        if purpose is not None:
            self._purpose = purpose
        if spent_at is not None:
            self._spent_at = spent_at
        if note is not None:
            self._note = note
        if reassign:
            self._organization_id = organization
        self._updated_at = now
        self._version += 1

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def amount(self) -> ExpenseAmount:
        return self._amount

    @property
    def category(self) -> ExpenseCategory:
        return self._category

    @property
    def purpose(self) -> ExpensePurpose:
        return self._purpose

    @property
    def spent_at(self) -> date:
        return self._spent_at

    @property
    def organization_id(self) -> uuid.UUID | None:
        return self._organization_id

    @property
    def note(self) -> ExpenseNote:
        return self._note or ExpenseNote()

    @property
    def recorded_by(self) -> uuid.UUID | None:
        return self._recorded_by

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def version(self) -> int:
        return self._version

    @property
    def persisted_version(self) -> int | None:
        return self._persisted_version

    def mark_persisted(self) -> None:
        """Called by the repository once the row matches this aggregate."""
        self._persisted_version = self._version
