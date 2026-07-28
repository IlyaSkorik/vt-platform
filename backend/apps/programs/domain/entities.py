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
    ProgramItemNotFoundError,
    ProgramShareNotFoundError,
    ReorderMismatchError,
)
from .value_objects import (
    DEFAULT_PUBLIC_COLUMNS,
    ItemDuration,
    ItemTitle,
    ProgramColumn,
    ProgramItemKind,
    ProgramName,
    PublicSlug,
    ShareName,
    TimeBuffer,
)

__all__ = ["Program", "ProgramItem", "ProgramShare"]

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
    """

    _id: uuid.UUID
    _kind: ProgramItemKind
    _duration: ItemDuration
    _title: ItemTitle | None = None
    _submission_id: uuid.UUID | None = None

    @classmethod
    def performance(cls, *, item_id: uuid.UUID, submission_id: uuid.UUID, duration: ItemDuration) -> ProgramItem:
        """Build a slot for one competing act."""
        return cls(_id=item_id, _kind=ProgramItemKind.PERFORMANCE, _duration=duration, _submission_id=submission_id)

    @classmethod
    def block(cls, *, item_id: uuid.UUID, kind: ProgramItemKind, title: ItemTitle, duration: ItemDuration) -> ProgramItem:
        """Build a standalone block (a break, and later an opening or an award)."""
        if kind.binds_performance:
            raise InvalidProgramDataError("A performance slot must be created with ProgramItem.performance().")
        return cls(_id=item_id, _kind=kind, _duration=duration, _title=title)

    @property
    def id(self) -> uuid.UUID:
        return self._id

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

    def retitle(self, title: ItemTitle) -> None:
        """Rename a standalone block."""
        if self._kind.binds_performance:
            raise InvalidProgramDataError("A performance slot takes its name from its act and cannot be retitled.")
        self._title = title

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ProgramItem) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"ProgramItem(id={self._id!r}, kind={self._kind.value!r}, duration={str(self._duration)!r})"


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
    _columns: tuple[ProgramColumn, ...] = ()
    _item_ids: tuple[uuid.UUID, ...] = ()
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
    def columns(self) -> tuple[ProgramColumn, ...]:
        """The columns this edition shows, in canonical order.

        Never empty: an edition published without a choice shows the default columns, so
        there is no state in which "no columns were chosen" has to be handled downstream.
        """
        return self._columns or DEFAULT_PUBLIC_COLUMNS

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

    def show_columns(self, columns: Sequence[ProgramColumn]) -> None:
        """Replace the set of columns this edition publishes."""
        self._columns = tuple(column for column in ProgramColumn if column in set(columns))

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
    _deleted_at: datetime | None = None
    _version: int = 1
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
        deleted_at: datetime | None = None,
        version: int = 1,
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
            _deleted_at=deleted_at,
            _version=version,
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
        return self._initial_version

    @property
    def performance_submission_ids(self) -> tuple[uuid.UUID, ...]:
        """The acts already in this program, in program order."""
        return tuple(item.submission_id for item in self._items if item.submission_id is not None)

    def item(self, item_id: uuid.UUID) -> ProgramItem:
        """Return one item, or raise :class:`ProgramItemNotFoundError`."""
        for candidate in self._items:
            if candidate.id == item_id:
                return candidate
        raise ProgramItemNotFoundError(f"Item {item_id} is not part of this program.")

    def share(self, share_id: uuid.UUID) -> ProgramShare:
        """Return one public edition, or raise :class:`ProgramShareNotFoundError`."""
        for candidate in self._shares:
            if candidate.id == share_id:
                return candidate
        raise ProgramShareNotFoundError(f"Public program {share_id} does not belong to this program.")

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
        """Give one competing act a slot (appended, or inserted at ``position``)."""
        if submission_id in self.performance_submission_ids:
            raise PerformanceAlreadyInProgramError(f"Act {submission_id} already has a slot in this program.")
        item = ProgramItem.performance(item_id=item_id, submission_id=submission_id, duration=duration)
        self._insert(item, position)
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
        self._touch(now)
        return item

    def remove_item(self, item_id: uuid.UUID, *, now: datetime) -> None:
        """Drop one slot. Shares that named it simply stop showing it."""
        item = self.item(item_id)
        self._items.remove(item)
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
        """
        wanted = list(ordered_item_ids)
        if len(wanted) != len(set(wanted)) or set(wanted) != {item.id for item in self._items}:
            raise ReorderMismatchError("A reorder must list every item of the program exactly once.")
        by_id = {item.id: item for item in self._items}
        self._items = [by_id[item_id] for item_id in wanted]
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
        columns: Sequence[ProgramColumn] = (),
        item_ids: Iterable[uuid.UUID] = (),
    ) -> ProgramShare:
        """Publish a named edition of this program behind its own slug.

        ``columns`` is what the edition is *for*: the columns of the table its reader
        sees. Passing none falls back to the default columns.

        ``item_ids`` optionally narrows the rows; pass none for "the whole program, kept
        current". Every id must belong to this program - an edition cannot point at a
        slot the organizer never made.
        """
        selection = tuple(dict.fromkeys(item_ids))
        known = {item.id for item in self._items}
        unknown = [str(item_id) for item_id in selection if item_id not in known]
        if unknown:
            raise ItemNotInProgramError(f"Items {', '.join(unknown)} are not part of this program.")
        share = ProgramShare(
            _id=share_id,
            _name=name,
            _slug=slug,
            _columns=tuple(column for column in ProgramColumn if column in set(columns)),
            _item_ids=selection,
            _created_at=now,
        )
        self._shares.append(share)
        self._touch(now)
        return share

    def rename_share(self, share_id: uuid.UUID, name: ShareName, *, now: datetime) -> ProgramShare:
        share = self.share(share_id)
        share.rename(name)
        self._touch(now)
        return share

    def set_share_columns(self, share_id: uuid.UUID, columns: Sequence[ProgramColumn], *, now: datetime) -> ProgramShare:
        """Change which columns a published edition shows, keeping its link."""
        share = self.share(share_id)
        share.show_columns(columns)
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
        """Soft-delete the program (and with it every public link into it)."""
        self._deleted_at = now
        self._touch(now)

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
