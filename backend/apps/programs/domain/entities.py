"""The ``Program`` aggregate root - the running order an organizer builds.

A program is **not** a view over the accepted submissions. It is its own entity
holding its own ordered :class:`ProgramItem` children, so the organizer can put an
act anywhere, drop a break between two of them, and keep that arrangement no matter
what happens to the submissions afterwards. That is also what makes the future
additions cheap: another kind of block (an opening, an award ceremony, a master
class) is a new :class:`~apps.programs.domain.value_objects.ProgramItemKind` and
nothing else, and a second stage is a second program.

The aggregate owns three things:

* **items** - the sequence itself. Order is the list's order; the position column in
  the database is a projection of it, never the source of truth.
* **buffer** - the padding every performance slot gets when the schedule is
  computed. It never touches an act's own duration.
* **shares** - the named public editions of this program (the task's
  ``ProgramView``, renamed so it cannot be confused with a DRF view). Each carries
  its own slug, so an organizer can hand the sound engineer items 25-40 and the
  screen by the stage the whole thing.

Framework-free (no Django, no DRF). Persistence lives in the infrastructure mapper.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime

from .exceptions import (
    InvalidProgramDataError,
    ItemNotInProgramError,
    PerformanceAlreadyInProgramError,
    ProgramColumnNotFoundError,
    ProgramHasSharesError,
    ProgramItemNotFoundError,
    ProgramNumbersFrozenError,
    ProgramShareNotFoundError,
    ReorderMismatchError,
)
from .value_objects import (
    DEFAULT_PUBLIC_COLUMNS,
    ArrangementSettings,
    CellValue,
    ColumnRef,
    ColumnTitle,
    ItemDuration,
    ItemTitle,
    ProgramColumn,
    ProgramItemKind,
    ProgramItemProgress,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
)

__all__ = ["CustomColumn", "Program", "ProgramItem", "ProgramShare"]

_CREATION_TOKEN = object()


@dataclass(slots=True, eq=False, repr=False)
class ProgramItem:
    """One slot in the running order.

    Every item, whatever its kind, has a duration - that is what lets the schedule
    be computed without knowing anything about kinds. A performance item points at
    its act by ``submission_id`` and carries no title of its own (the name of the
    act and of its participants is read live, so a corrected name shows up
    everywhere at once). A standalone block is the mirror image: a title it owns, no
    submission.

    A performance item's duration is **seeded** from the act's declared length and
    then belongs to the program: an organizer sizing a slot by hand is making a
    decision about the event, not about the act.

    :attr:`number` is the slot's number in the program, and its meaning changes exactly
    once - when the program is first published. Until then nobody has been told anything,
    so numbers simply follow the running order and are re-issued freely on every change.
    After the first public link exists they are **frozen**: rearranging the order then
    rearranges the rows and not the numbers, so a program legitimately reads 2, 3, 5, 4.
    See :meth:`Program.freeze_numbers`.

    A standalone block carries ``0``, meaning "no number": a break is a gap in the running
    order rather than an act, and numbering it would push every act after it one place
    along. See :attr:`ProgramItemKind.takes_number`.
    """

    _id: uuid.UUID
    _kind: ProgramItemKind
    _duration: ItemDuration
    _number: int = 0
    _title: ItemTitle | None = None
    _submission_id: uuid.UUID | None = None
    #: Hand-filled values, keyed by custom column id. Absent means blank.
    _custom_values: dict[uuid.UUID, CellValue] = field(default_factory=dict)
    #: How far this slot has got on the day itself (the host drives it).
    _progress: ProgramItemProgress = ProgramItemProgress.PENDING

    @classmethod
    def performance(
        cls,
        *,
        item_id: uuid.UUID,
        submission_id: uuid.UUID,
        duration: ItemDuration,
        number: int = 0,
        custom_values: dict[uuid.UUID, CellValue] | None = None,
        progress: ProgramItemProgress = ProgramItemProgress.PENDING,
    ) -> ProgramItem:
        """Build a slot for one competing act."""
        return cls(
            _id=item_id,
            _kind=ProgramItemKind.PERFORMANCE,
            _duration=duration,
            _number=number,
            _submission_id=submission_id,
            _custom_values=dict(custom_values or {}),
            _progress=progress,
        )

    @classmethod
    def block(
        cls,
        *,
        item_id: uuid.UUID,
        kind: ProgramItemKind,
        title: ItemTitle,
        duration: ItemDuration,
        number: int = 0,
        custom_values: dict[uuid.UUID, CellValue] | None = None,
        progress: ProgramItemProgress = ProgramItemProgress.PENDING,
    ) -> ProgramItem:
        """Build a standalone block (a break, and later an opening or an award)."""
        if kind.binds_performance:
            raise InvalidProgramDataError("A performance slot must be created with ProgramItem.performance().")
        return cls(
            _id=item_id,
            _kind=kind,
            _duration=duration,
            _number=number,
            _title=title,
            _custom_values=dict(custom_values or {}),
            _progress=progress,
        )

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def number(self) -> int:
        """This slot's number in the program (frozen once the program is published)."""
        return self._number

    @property
    def kind(self) -> ProgramItemKind:
        return self._kind

    @property
    def duration(self) -> ItemDuration:
        return self._duration

    @property
    def title(self) -> ItemTitle | None:
        return self._title

    @property
    def submission_id(self) -> uuid.UUID | None:
        return self._submission_id

    def resize(self, duration: ItemDuration) -> None:
        """Set the slot's length (the organizer's decision about the event)."""
        self._duration = duration

    @property
    def progress(self) -> ProgramItemProgress:
        """How far this slot has got on the day itself."""
        return self._progress

    @property
    def custom_values(self) -> dict[uuid.UUID, CellValue]:
        """Hand-filled values by custom column id (a copy; use :meth:`fill` to change)."""
        return dict(self._custom_values)

    def value_in(self, column_id: uuid.UUID) -> CellValue:
        """This slot's value in one custom column - blank when nothing was filled in."""
        return self._custom_values.get(column_id, CellValue())

    def fill(self, column_id: uuid.UUID, value: CellValue) -> None:
        """Set (or clear) this slot's value in one custom column."""
        if value.is_blank:
            self._custom_values.pop(column_id, None)
        else:
            self._custom_values[column_id] = value

    def forget_column(self, column_id: uuid.UUID) -> None:
        """Drop the value for a column that no longer exists."""
        self._custom_values.pop(column_id, None)

    def set_progress(self, progress: ProgramItemProgress) -> None:
        """Record how far this slot has got. Only the aggregate may call this."""
        self._progress = progress

    def assign_number(self, number: int) -> None:
        """Set this slot's number. Only the aggregate may call this."""
        self._number = number

    def retitle(self, title: ItemTitle) -> None:
        """Rename a standalone block."""
        if self._kind.binds_performance:
            raise InvalidProgramDataError("Название строки выступления берётся из номера и не меняется вручную.")
        self._title = title

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ProgramItem) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"ProgramItem(id={self._id!r}, kind={self._kind.value!r}, duration={str(self._duration)!r})"


@dataclass(slots=True, eq=False, repr=False)
class CustomColumn:
    """A column the organizer added to this programme and fills in by hand.

    The escape hatch for whatever a particular festival needs and the built-in vocabulary
    does not have - "микрофон", "реквизит", "оплачено". It is owned by the programme, so
    two programmes never share one, and it behaves like any other column downstream: it
    can be published on a link and it renders into a cell.
    """

    _id: uuid.UUID
    _title: ColumnTitle

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def title(self) -> ColumnTitle:
        return self._title

    @property
    def ref(self) -> ColumnRef:
        """This column as a reference a share can select."""
        return ColumnRef.custom(self._id)

    def rename(self, title: ColumnTitle) -> None:
        """Rename the column. Its id - and so every value in it - is untouched."""
        self._title = title

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CustomColumn) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"CustomColumn(id={self._id!r}, title={str(self._title)!r})"


@dataclass(slots=True, eq=False, repr=False)
class ProgramShare:
    """A named public edition of the program, reachable by its own slug.

    An edition is defined by **which columns of the table it shows**: the sound engineer
    needs the time, the act and its notes; the screen beside the stage needs the time,
    the participant and the act. That is the selection an organizer makes when
    publishing, and :attr:`columns` is it. An empty selection falls back to
    :data:`DEFAULT_PUBLIC_COLUMNS` rather than showing everything, because a public link
    must never expose a column by accident.

    ``item_ids`` optionally narrows the *rows* as well ("пункты 25-40"), and is a
    selection over the program rather than a copy of it: rows are always rendered in the
    program's current order, and an item removed from the program simply stops appearing.
    An **empty row selection means the whole program** - and keeps meaning that as the
    program grows, which is the difference between a link that stays right and one that
    silently freezes on the day it was created.
    """

    _id: uuid.UUID
    _name: ShareName
    _slug: PublicSlug
    _columns: tuple[ColumnRef, ...] = ()
    _item_ids: tuple[uuid.UUID, ...] = ()
    #: Whether whoever holds this link may drive the running order on the day: mark an
    #: act as on stage or performed, and rearrange what is still to come. The host's
    #: edition; every other link stays read-only.
    _controls_running_order: bool = False
    _created_at: datetime | None = None

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def name(self) -> ShareName:
        return self._name

    @property
    def slug(self) -> PublicSlug:
        return self._slug

    @property
    def item_ids(self) -> tuple[uuid.UUID, ...]:
        return self._item_ids

    @property
    def columns(self) -> tuple[ColumnRef, ...]:
        """The columns this edition shows, left to right as the organizer arranged them.

        The order is part of the edition, not of the programme: the sound desk wants the
        time and the act first, the screen beside the stage wants the participant, and
        whoever publishes the link is the one who knows which. A reader of a public
        screen never scrolls to find the column their job depends on.

        Never empty: an edition published without a choice shows the default columns, so
        there is no state in which "no columns were chosen" has to be handled downstream.
        """
        return self._columns or tuple(ColumnRef.of(column) for column in DEFAULT_PUBLIC_COLUMNS)

    @property
    def controls_running_order(self) -> bool:
        """Whether this link may drive the running order (the host's edition)."""
        return self._controls_running_order

    @property
    def created_at(self) -> datetime | None:
        return self._created_at

    @property
    def covers_whole_program(self) -> bool:
        """Whether this share follows every row rather than a fixed set of them."""
        return not self._item_ids

    def rename(self, name: ShareName) -> None:
        """Rename the public edition (its slug, and therefore its link, is permanent)."""
        self._name = name

    def show_columns(self, columns: Sequence[ColumnRef]) -> None:
        """Replace the set of columns this edition publishes (already normalized)."""
        self._columns = tuple(columns)

    def set_control(self, *, allowed: bool) -> None:
        """Grant or withdraw the right to drive the running order from this link."""
        self._controls_running_order = allowed

    def drop_column(self, column_id: uuid.UUID) -> None:
        """Stop publishing a custom column that no longer exists."""
        self._columns = tuple(ref for ref in self._columns if ref.custom_id != column_id)

    def selects(self, item_id: uuid.UUID) -> bool:
        """Whether ``item_id`` is part of this edition."""
        return self.covers_whole_program or item_id in self._item_ids

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ProgramShare) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"ProgramShare(id={self._id!r}, name={str(self._name)!r}, slug={str(self._slug)!r})"


@dataclass(slots=True, eq=False, repr=False)
class Program:
    """The Program aggregate root - one running order for one competition.

    Scoped to a competition and, usually, to one nomination ("Вокал", "Хореография"),
    which is how organizers actually build a day. ``nomination_id`` may be ``None``
    for a program that spans the whole competition. Equality is by id.
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _competition_id: uuid.UUID
    _name: ProgramName
    _created_at: datetime
    _updated_at: datetime
    _nomination_id: uuid.UUID | None = None
    _starts_at: datetime | None = None
    _buffer: TimeBuffer = field(default_factory=TimeBuffer.none)
    _items: list[ProgramItem] = field(default_factory=list)
    _shares: list[ProgramShare] = field(default_factory=list)
    _custom_columns: list[CustomColumn] = field(default_factory=list)
    #: How many numbers this program has issued since freezing. Monotonic, so a removed
    #: slot's number is retired rather than reused - see :meth:`_next_number`.
    _numbers_issued: int = 0
    #: When the numbers stopped following the running order - the moment of the first
    #: publication. ``None`` while the program is still being assembled.
    _numbers_frozen_at: datetime | None = None
    _deleted_at: datetime | None = None
    _version: int = 1
    #: The rules the running order was last generated from, kept so "пересобрать" is one
    #: button rather than a settings form refilled from memory. ``None`` for a programme
    #: that was only ever built by hand.
    _arrangement: ArrangementSettings | None = None
    #: The version this aggregate was loaded at - the optimistic-concurrency
    #: pre-image the repository writes against. Transient (never persisted).
    _initial_version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise InvalidProgramDataError("Program must be created via Program.create() or Program.rehydrate().")

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        program_id: uuid.UUID,
        competition_id: uuid.UUID,
        name: ProgramName,
        now: datetime,
        nomination_id: uuid.UUID | None = None,
        starts_at: datetime | None = None,
        buffer: TimeBuffer | None = None,
    ) -> Program:
        """Create an empty program. Items and shares are added afterwards."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=program_id,
            _competition_id=competition_id,
            _name=name,
            _created_at=now,
            _updated_at=now,
            _nomination_id=nomination_id,
            _starts_at=starts_at,
            _buffer=buffer if buffer is not None else TimeBuffer.none(),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        program_id: uuid.UUID,
        competition_id: uuid.UUID,
        name: ProgramName,
        created_at: datetime,
        updated_at: datetime,
        nomination_id: uuid.UUID | None = None,
        starts_at: datetime | None = None,
        buffer: TimeBuffer | None = None,
        items: Sequence[ProgramItem] = (),
        shares: Sequence[ProgramShare] = (),
        custom_columns: Sequence[CustomColumn] = (),
        numbers_issued: int = 0,
        numbers_frozen_at: datetime | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
        arrangement: ArrangementSettings | None = None,
    ) -> Program:
        """Reconstruct the aggregate from persistence (no re-validation)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=program_id,
            _competition_id=competition_id,
            _name=name,
            _created_at=created_at,
            _updated_at=updated_at,
            _nomination_id=nomination_id,
            _starts_at=starts_at,
            _buffer=buffer if buffer is not None else TimeBuffer.none(),
            _items=list(items),
            _shares=list(shares),
            _custom_columns=list(custom_columns),
            _numbers_issued=numbers_issued,
            _numbers_frozen_at=numbers_frozen_at,
            _deleted_at=deleted_at,
            _version=version,
            _arrangement=arrangement,
            _initial_version=version,
        )

    # ------------------------------------------------------------------
    # Read-only views
    # ------------------------------------------------------------------

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def competition_id(self) -> uuid.UUID:
        return self._competition_id

    @property
    def nomination_id(self) -> uuid.UUID | None:
        return self._nomination_id

    @property
    def name(self) -> ProgramName:
        return self._name

    @property
    def starts_at(self) -> datetime | None:
        return self._starts_at

    @property
    def buffer(self) -> TimeBuffer:
        return self._buffer

    @property
    def arrangement(self) -> ArrangementSettings | None:
        """The rules this running order was last generated from, if it ever was."""
        return self._arrangement

    @property
    def items(self) -> tuple[ProgramItem, ...]:
        """The running order, in order."""
        return tuple(self._items)

    @property
    def shares(self) -> tuple[ProgramShare, ...]:
        return tuple(self._shares)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def version(self) -> int:
        return self._version

    @property
    def initial_version(self) -> int:
        """The version this copy was read at — the repository's optimistic pre-image."""
        return self._initial_version

    def mark_persisted(self) -> None:
        """Mark this in-memory instance as clean at its current version.

        Called by the repository after a successful write, so the next save of the same
        instance uses the just-persisted version as its pre-image. One use case may bump
        the version several times before a single save, and the same instance may be
        saved more than once; neither is a conflict.
        """
        self._initial_version = self._version

    @property
    def numbers_issued(self) -> int:
        """The highest number this program has handed out since freezing (never decreases)."""
        return max(self._numbers_issued, *(item.number for item in self._items)) if self._items else self._numbers_issued

    @property
    def numbers_frozen_at(self) -> datetime | None:
        """When the numbers stopped following the running order, if they have."""
        return self._numbers_frozen_at

    @property
    def numbers_frozen(self) -> bool:
        """Whether numbers are fixed to their slots rather than to their positions.

        ``False`` while the program is still being assembled - nobody has been told a
        number yet, so there is nothing to protect and numbers simply follow the order.
        """
        return self._numbers_frozen_at is not None

    @property
    def performance_submission_ids(self) -> tuple[uuid.UUID, ...]:
        """The acts already in this program, in program order."""
        return tuple(item.submission_id for item in self._items if item.submission_id is not None)

    def item(self, item_id: uuid.UUID) -> ProgramItem:
        """Return one item, or raise :class:`ProgramItemNotFoundError`."""
        for candidate in self._items:
            if candidate.id == item_id:
                return candidate
        raise ProgramItemNotFoundError("Этой строки нет в программе — обновите страницу.")

    def share(self, share_id: uuid.UUID) -> ProgramShare:
        """Return one public edition, or raise :class:`ProgramShareNotFoundError`."""
        for candidate in self._shares:
            if candidate.id == share_id:
                return candidate
        raise ProgramShareNotFoundError("Эта публичная ссылка относится к другой программе.")

    @property
    def custom_columns(self) -> tuple[CustomColumn, ...]:
        """The columns the organizer added to this programme, in their own order."""
        return tuple(self._custom_columns)

    @property
    def columns(self) -> tuple[ColumnRef, ...]:
        """Every column this programme can carry: the built-ins, then its custom ones."""
        return tuple(ColumnRef.of(column) for column in ProgramColumn) + tuple(column.ref for column in self._custom_columns)

    @property
    def on_stage(self) -> ProgramItem | None:
        """The slot currently on stage, if the host has marked one."""
        for item in self._items:
            if item.progress is ProgramItemProgress.ON_STAGE:
                return item
        return None

    def custom_column(self, column_id: uuid.UUID) -> CustomColumn:
        """Return one custom column, or raise :class:`ProgramColumnNotFoundError`."""
        for candidate in self._custom_columns:
            if candidate.id == column_id:
                return candidate
        raise ProgramColumnNotFoundError("Этой колонки нет в программе — обновите страницу.")

    def select_columns(self, refs: Sequence[ColumnRef | ProgramColumn]) -> tuple[ColumnRef, ...]:
        """Take a selection in the order it was given, rejecting anything this programme has not got.

        The one way a cut of this table is chosen, for a printed page and for a published
        link alike: both are laid out for one job by the person who knows it — the number
        and the act first for the sound desk, the organization first for the register —
        and that order is theirs rather than the enum's.

        Accepts a bare :class:`ProgramColumn` as a convenience - naming a built-in column
        should not require wrapping it first.

        A column named twice collapses onto its first mention: a table cannot carry the
        same column in two places, and refusing the whole export over it would be rude.
        """
        chosen: list[ColumnRef] = []
        for ref in refs:
            column = ref if isinstance(ref, ColumnRef) else ColumnRef.of(ref)
            if column not in chosen:
                chosen.append(column)
        known = {column.id for column in self._custom_columns}
        unknown = [ref.key for ref in chosen if ref.is_custom and ref.custom_id not in known]
        if unknown:
            raise ProgramColumnNotFoundError("Некоторых колонок нет в программе — обновите страницу.")
        return tuple(chosen)

    # ------------------------------------------------------------------
    # Custom columns
    # ------------------------------------------------------------------

    def add_custom_column(self, *, column_id: uuid.UUID, title: ColumnTitle, now: datetime) -> CustomColumn:
        """Add a column of the organizer's own, appended after the existing ones."""
        column = CustomColumn(_id=column_id, _title=title)
        self._custom_columns.append(column)
        self._touch(now)
        return column

    def rename_custom_column(self, column_id: uuid.UUID, title: ColumnTitle, *, now: datetime) -> CustomColumn:
        """Rename a custom column, keeping its id and therefore every value in it."""
        column = self.custom_column(column_id)
        column.rename(title)
        self._touch(now)
        return column

    def remove_custom_column(self, column_id: uuid.UUID, *, now: datetime) -> None:
        """Drop a custom column, its values, and its place on every published link.

        Deliberately cascading: leaving a published edition pointing at a column that no
        longer exists would render a header with nothing under it.
        """
        column = self.custom_column(column_id)
        self._custom_columns.remove(column)
        for item in self._items:
            item.forget_column(column_id)
        for share in self._shares:
            share.drop_column(column_id)
        self._touch(now)

    def fill_cell(self, *, item_id: uuid.UUID, column_id: uuid.UUID, value: CellValue, now: datetime) -> ProgramItem:
        """Write one hand-filled cell (blank clears it)."""
        self.custom_column(column_id)
        item = self.item(item_id)
        item.fill(column_id, value)
        self._touch(now)
        return item

    # ------------------------------------------------------------------
    # The day itself
    # ------------------------------------------------------------------

    def set_item_progress(self, item_id: uuid.UUID, progress: ProgramItemProgress, *, now: datetime) -> ProgramItem:
        """Record how far one slot has got, as the host announces the day.

        Putting a slot on stage takes the previous one off it and counts it as performed:
        an act ends when the next one begins, and a host should not have to say so twice.
        At most one slot is ever on stage.
        """
        item = self.item(item_id)
        if progress is ProgramItemProgress.ON_STAGE:
            for other in self._items:
                if other.id != item_id and other.progress is ProgramItemProgress.ON_STAGE:
                    other.set_progress(ProgramItemProgress.PERFORMED)
        item.set_progress(progress)
        self._touch(now)
        return item

    def reset_progress(self, *, now: datetime) -> None:
        """Put every slot back to pending - a rehearsal run, or a false start."""
        for item in self._items:
            item.set_progress(ProgramItemProgress.PENDING)
        self._touch(now)

    # ------------------------------------------------------------------
    # Program-level settings
    # ------------------------------------------------------------------

    def rename(self, name: ProgramName, *, now: datetime) -> None:
        self._name = name
        self._touch(now)

    def set_buffer(self, buffer: TimeBuffer, *, now: datetime) -> None:
        """Change the padding applied to performance slots.

        Affects only how the schedule is computed - no act's duration changes, which
        is why this is a single program-level setting and not an edit of every item.
        """
        self._buffer = buffer
        self._touch(now)

    def set_start(self, starts_at: datetime | None, *, now: datetime) -> None:
        """Set (or clear) the wall-clock time the first item begins at.

        Without it the program still has a shape - every item keeps its offset from
        the start - it just has no clock times to show yet.
        """
        self._starts_at = starts_at
        self._touch(now)

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def add_performance(
        self,
        *,
        item_id: uuid.UUID,
        submission_id: uuid.UUID,
        duration: ItemDuration,
        now: datetime,
        position: int | None = None,
    ) -> ProgramItem:
        """Give one competing act a slot (appended, or inserted at ``position``).

        Before the program is published the whole running order is renumbered, so numbers
        stay 1..N while it is still being assembled. Afterwards the new slot takes the
        next free number and nobody else's changes.
        """
        if submission_id in self.performance_submission_ids:
            raise PerformanceAlreadyInProgramError("Это выступление уже стоит в программе.")
        item = ProgramItem.performance(item_id=item_id, submission_id=submission_id, duration=duration)
        self._insert(item, position)
        self._number_new_item(item)
        self._touch(now)
        return item

    def add_block(
        self,
        *,
        item_id: uuid.UUID,
        kind: ProgramItemKind,
        title: ItemTitle,
        duration: ItemDuration,
        now: datetime,
        position: int | None = None,
    ) -> ProgramItem:
        """Insert a standalone block - a break, and in future an opening or an award."""
        item = ProgramItem.block(item_id=item_id, kind=kind, title=title, duration=duration)
        self._insert(item, position)
        self._number_new_item(item)
        self._touch(now)
        return item

    def remove_item(self, item_id: uuid.UUID, *, now: datetime) -> None:
        """Drop one slot. Shares that named it simply stop showing it.

        Before publication the rest close the gap and are renumbered; afterwards the
        number goes with the slot and is retired.
        """
        item = self.item(item_id)
        self._items.remove(item)
        if not self.numbers_frozen:
            self._renumber_following_order()
        self._touch(now)

    def edit_item(
        self,
        item_id: uuid.UUID,
        *,
        now: datetime,
        title: ItemTitle | None = None,
        duration: ItemDuration | None = None,
    ) -> ProgramItem:
        """Retitle and/or resize one slot (a break's length, a stretched act)."""
        item = self.item(item_id)
        if title is not None:
            item.retitle(title)
        if duration is not None:
            item.resize(duration)
        self._touch(now)
        return item

    def reorder(self, ordered_item_ids: Sequence[uuid.UUID], *, now: datetime) -> None:
        """Rearrange the whole running order.

        Takes the complete new order rather than a move instruction: the request then
        carries what the organizer sees, and a stale client cannot half-apply a move.

        While the program is unpublished the numbers follow the new order - it is still
        being assembled and nobody has been told anything. Once published they travel with
        their slots instead, so swapping two acts because a participant asked to go later
        leaves the programme reading 2, 3, 5, 4: номер 4 was promised to that participant
        and is still theirs.
        """
        wanted = list(ordered_item_ids)
        if len(wanted) != len(set(wanted)) or set(wanted) != {item.id for item in self._items}:
            raise ReorderMismatchError("Порядок задан неверно: список должен содержать все строки ровно по одному разу.")
        by_id = {item.id: item for item in self._items}
        self._items = [by_id[item_id] for item_id in wanted]
        if not self.numbers_frozen:
            self._renumber_following_order()
        self._touch(now)

    def rebuild(self, items: Sequence[ProgramItem], *, settings: ArrangementSettings, now: datetime) -> None:
        """Replace the whole running order with a generated one, and remember its rules.

        Regeneration is a replacement, not a merge: the organizer asked for the day the
        rules describe, and an order half-made by hand and half by rule is one neither
        of them can explain. Every slot is new, so everything a slot carried by hand goes
        with it - a break moved by eye, a resized act, a filled-in "Микрофон" cell. The
        columns themselves stay; their values do not. That is the trade the "пересобрать"
        button makes, and the dialog says so before it is taken.

        Refused outright once the numbers are frozen: they have been published, and no
        set of rules is worth telling a participant their number changed.
        """
        if self.numbers_frozen:
            raise ProgramNumbersFrozenError("Программа уже опубликована — номера закреплены, пересобрать её нельзя.")
        self._items = list(items)
        self._renumber_following_order()
        self._arrangement = settings
        self._touch(now)

    def freeze_numbers(self, *, now: datetime) -> None:
        """Fix the numbers to their slots, from now on.

        Called when the program is first published, because that is the moment the numbers
        leave the organizer's screen and reach the people they are about. Idempotent: a
        second publication does not re-freeze, and so cannot disturb numbers that are
        already out there.
        """
        if self.numbers_frozen:
            return
        self._numbers_issued = self._renumber_following_order()
        self._numbers_frozen_at = now

    def renumber_sequentially(self, *, now: datetime) -> None:
        """Re-issue numbers 1..N following the current running order.

        The deliberate way out of a published programme whose numbers have drifted far
        from its order - offered as its own action precisely because it invalidates every
        number already told to a participant, and so must never happen as a side effect of
        a reorder.
        """
        self._numbers_issued = self._renumber_following_order()
        self._touch(now)

    # ------------------------------------------------------------------
    # Public editions (shares)
    # ------------------------------------------------------------------

    def add_share(
        self,
        *,
        share_id: uuid.UUID,
        name: ShareName,
        slug: PublicSlug,
        now: datetime,
        columns: Sequence[ColumnRef | ProgramColumn] = (),
        item_ids: Iterable[uuid.UUID] = (),
        controls_running_order: bool = False,
    ) -> ProgramShare:
        """Publish a named edition of this program behind its own slug.

        ``columns`` is what the edition is *for*: the columns of the table its reader
        sees, in the order they are given. Passing none falls back to the default columns.

        ``item_ids`` optionally narrows the rows; pass none for "the whole program, kept
        current". Every id must belong to this program - an edition cannot point at a
        slot the organizer never made.

        ``controls_running_order`` makes this the **host's** edition: whoever holds the link
        may mark an act as on stage or performed and rearrange what is still to come. Every
        other link stays read-only, so the one handed to an audience cannot change the day.

        Publishing for the first time **freezes the numbers**: this is the moment they stop
        being a working draft and become what participants are told.
        """
        selection = tuple(dict.fromkeys(item_ids))
        known = {item.id for item in self._items}
        unknown = [str(item_id) for item_id in selection if item_id not in known]
        if unknown:
            raise ItemNotInProgramError("Некоторых строк нет в программе — обновите страницу.")
        share = ProgramShare(
            _id=share_id,
            _name=name,
            _slug=slug,
            _columns=self.select_columns(columns),
            _item_ids=selection,
            _controls_running_order=controls_running_order,
            _created_at=now,
        )
        self._shares.append(share)
        self.freeze_numbers(now=now)
        self._touch(now)
        return share

    def rename_share(self, share_id: uuid.UUID, name: ShareName, *, now: datetime) -> ProgramShare:
        share = self.share(share_id)
        share.rename(name)
        self._touch(now)
        return share

    def set_share_columns(self, share_id: uuid.UUID, columns: Sequence[ColumnRef | ProgramColumn], *, now: datetime) -> ProgramShare:
        """Change which columns a published edition shows — and their order — keeping its link."""
        share = self.share(share_id)
        share.show_columns(self.select_columns(columns))
        self._touch(now)
        return share

    def set_share_control(self, share_id: uuid.UUID, *, allowed: bool, now: datetime) -> ProgramShare:
        """Grant or withdraw a link's right to drive the running order."""
        share = self.share(share_id)
        share.set_control(allowed=allowed)
        self._touch(now)
        return share

    def remove_share(self, share_id: uuid.UUID, *, now: datetime) -> None:
        """Revoke a public edition. Its link stops resolving immediately."""
        share = self.share(share_id)
        self._shares.remove(share)
        self._touch(now)

    def items_for(self, share: ProgramShare) -> tuple[ProgramItem, ...]:
        """The items one edition shows, in the program's current order."""
        return tuple(item for item in self._items if share.selects(item.id))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def delete(self, *, now: datetime) -> None:
        """Soft-delete the program, provided no public link still leads into it.

        Refused while any edition is published: deleting would take the sound desk's
        copy, the host's copy and the one mailed to participants down with it, each of
        them silently (see :class:`ProgramHasSharesError`). Revoking the links first is
        the organizer's own confirmation that nobody is reading this any more.
        """
        if self._shares:
            raise ProgramHasSharesError(f"Программа «{self._name}» опубликована по {len(self._shares)} ссылке(ам) — сначала отзовите их.")
        self._deleted_at = now
        self._touch(now)

    def _number_new_item(self, item: ProgramItem) -> None:
        """Number a freshly inserted slot according to which phase the program is in."""
        if not item.kind.takes_number:
            # A break takes no number, and must not spend one either: inserting it into a
            # published programme would otherwise retire a number nobody ever performed as.
            item.assign_number(0)
            return
        if self.numbers_frozen:
            item.assign_number(self._next_number())
        else:
            self._renumber_following_order()

    def _renumber_following_order(self) -> int:
        """Make the numbers 1..N in running order, and answer how many were issued.

        Only the slots that take a number are counted - a break sits in the order and
        carries 0, so an act after a lunch break is номер 12 rather than номер 13. See
        :attr:`ProgramItemKind.takes_number`.
        """
        issued = 0
        for item in self._items:
            if item.kind.takes_number:
                issued += 1
                item.assign_number(issued)
            else:
                item.assign_number(0)
        return issued

    def _next_number(self) -> int:
        """Issue the next number: one past the highest this program has given out.

        Deliberately a monotonic counter rather than ``max(present numbers) + 1``: once
        frozen, a removed slot's number must be **retired**, not handed to the next act. A
        participant told "номер 4" must never find somebody else performing as номер 4,
        including after theirs was withdrawn.
        """
        self._numbers_issued = self.numbers_issued + 1
        return self._numbers_issued

    def _insert(self, item: ProgramItem, position: int | None) -> None:
        """Place ``item`` at a 1-based ``position``, or append when it is ``None``."""
        if position is None:
            self._items.append(item)
            return
        index = max(0, min(len(self._items), position - 1))
        self._items.insert(index, item)

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Program) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Program(id={self._id!r}, name={str(self._name)!r}, items={len(self._items)})"
