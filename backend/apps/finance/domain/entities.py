"""The Finance context's aggregates: what the platform spent, and what it received.

Two records, both entered by hand, both the half of the books that no projection
can derive.

:class:`PlatformExpense` is what the platform *spends*: hosting, a contractor, an
advertisement, a bank fee. Nothing in the system knows about those.

:class:`CommissionPayment` is what an organization *paid*. The commission it owes
is derived — the dashboard counts its performances and applies its terms — but
whether the money actually arrived is a fact only the operator's bank statement
carries. Without this record the console could show what was owed and never what
was settled, which made the one question worth asking ("who still owes us?")
unanswerable.

What follows describes :class:`PlatformExpense`; the second aggregate documents
its own decisions at its definition.

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

from .exceptions import InvalidCommissionPaymentDataError, InvalidExpenseDataError
from .value_objects import ExpenseAmount, ExpenseCategory, ExpenseNote, ExpensePurpose, PaymentAmount, PaymentNote

__all__ = ["CommissionPayment", "PlatformExpense"]

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


@dataclass(slots=True, eq=False, repr=False)
class CommissionPayment:
    """One sum an organization actually paid the platform, entered by hand.

    The counterpart to the commission the dashboard *computes*. That figure says
    what an organization owes once its performances are counted; it says nothing
    about whether the money arrived, and until this record existed the console had
    no way to tell the two apart — an organization that had paid in full looked
    exactly like one that had not paid at all.

    Three decisions shape it, and they are not the expense book's.

    **An organization is required.** An expense may belong to nobody, because the
    platform really does carry costs for itself. A commission receipt always has a
    payer: it exists to be subtracted from one organization's debt, and one with no
    payer would be money that reduces nothing.

    **There is no purpose field.** What the money was for is the commission — that
    is the whole ledger. :class:`~apps.finance.domain.value_objects.PaymentNote`
    carries the payment order number and the period, which is the detail that
    actually varies.

    **It is correctable, not immutable.** The operator's own bookkeeping, like the
    expense book: a mistyped sum is a wrong debt figure until it is fixed.
    :meth:`amend` is that fix; removal is the repository's soft delete.

    ``received_at`` is a :class:`datetime.date` and not an instant — money arrives
    on a day, the bank statement says which, and the hour it was typed into the
    console is ``created_at`` beside it.

    Framework-free (no Django, no DRF, no clock, no IO): time always arrives as ``now``.
    """

    _token: InitVar[object]
    _id: uuid.UUID
    #: Who paid. Required, unlike an expense's — see the class docstring.
    _organization_id: uuid.UUID
    _amount: PaymentAmount
    _received_at: date
    _created_at: datetime
    _updated_at: datetime
    _note: PaymentNote | None = None
    #: Which operator recorded it. A bare id: this context has no business knowing
    #: what people are called, and the console resolves the name it shows.
    _recorded_by: uuid.UUID | None = None
    _version: int = 1
    #: The version this aggregate was last read at, or ``None`` for one never stored.
    _persisted_version: int | None = None

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise InvalidCommissionPaymentDataError("CommissionPayment must be created via record() or rehydrate().")
        if not isinstance(self._organization_id, uuid.UUID):
            raise InvalidCommissionPaymentDataError("Укажите организацию, от которой поступили деньги.")
        if self._note is None:
            self._note = PaymentNote()

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def record(
        cls,
        *,
        payment_id: uuid.UUID,
        organization_id: uuid.UUID,
        amount: PaymentAmount,
        received_at: date,
        now: datetime,
        note: PaymentNote | None = None,
        recorded_by: uuid.UUID | None = None,
    ) -> CommissionPayment:
        """Enter one receipt into the books."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=payment_id,
            _organization_id=organization_id,
            _amount=amount,
            _received_at=received_at,
            _created_at=now,
            _updated_at=now,
            _note=note or PaymentNote(),
            _recorded_by=recorded_by,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        payment_id: uuid.UUID,
        organization_id: uuid.UUID,
        amount: PaymentAmount,
        received_at: date,
        created_at: datetime,
        updated_at: datetime,
        note: PaymentNote | None = None,
        recorded_by: uuid.UUID | None = None,
        version: int = 1,
    ) -> CommissionPayment:
        """Rebuild a stored receipt without re-running its creation rules."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=payment_id,
            _organization_id=organization_id,
            _amount=amount,
            _received_at=received_at,
            _created_at=created_at,
            _updated_at=updated_at,
            _note=note or PaymentNote(),
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
        amount: PaymentAmount | None = None,
        received_at: date | None = None,
        note: PaymentNote | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> None:
        """Correct a recorded receipt. ``None`` everywhere means "leave as it was".

        ``organization_id`` needs no ``reassign`` flag of the kind
        :meth:`PlatformExpense.amend` carries: a receipt always has a payer, so
        ``None`` here can only mean "unchanged" and never "move it off the client".
        Re-pointing a receipt at a different organization is still allowed — that is
        what a payment credited to the wrong client needs.
        """
        if amount is not None:
            self._amount = amount
        if received_at is not None:
            self._received_at = received_at
        if note is not None:
            self._note = note
        if organization_id is not None:
            self._organization_id = organization_id
        self._updated_at = now
        self._version += 1

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def organization_id(self) -> uuid.UUID:
        return self._organization_id

    @property
    def amount(self) -> PaymentAmount:
        return self._amount

    @property
    def received_at(self) -> date:
        return self._received_at

    @property
    def note(self) -> PaymentNote:
        return self._note or PaymentNote()

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
