"""The ``Protocol`` aggregate root - the jury's results for one nomination.

A protocol is the table the jury fills in and the organizer publishes. It is **its
own entity**, not a view over the programme it was seeded from: the running order can
be rearranged after the ceremony, an act can be withdrawn from the day, and none of
that may move a result that has already been awarded. Seeding copies the order and the
numbers once; from then on the protocol is the record.

The aggregate owns two things:

* **rows** - one per competing act, in the order they performed, each carrying the
  award the jury gave it (or nothing yet). The row *is* the result.
* **the published version** - which columns the public page shows, the permanent slug
  it is reached by, and which revision of the results is currently out there.

Two rules are worth stating here because everything else follows from them:

**An award can always be changed.** Not a workflow with a point of no return: a jury
enters "Лауреат II степени" and corrects it to "Лауреат I степени" ten minutes later,
and after the ceremony a typo in a nomination's results is a real thing that has to be
fixable. Every write path onto a row therefore accepts any award at any status,
including clearing it.

**Publication is what makes results real, and it is repeatable.** Until
:meth:`publish` nothing has left the organization - no link, no diploma degree, no
mail. Publishing raises :attr:`revision` and stamps :attr:`published_at`, and the slug
is minted once and never changes, so a corrected protocol is the same document at a
higher revision rather than a second URL nobody knows about.

Framework-free (no Django, no DRF). Persistence lives in the infrastructure mapper.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime

from .exceptions import (
    AwardsIncompleteError,
    InvalidProtocolDataError,
    PerformanceAlreadyInProtocolError,
    ProtocolRowNotFoundError,
    ReorderMismatchError,
)
from .value_objects import (
    DEFAULT_PUBLIC_COLUMNS,
    AwardKind,
    ProtocolColumn,
    ProtocolName,
    ProtocolStatus,
    PublicSlug,
    PublishedResult,
    PublishedSnapshot,
)

__all__ = ["Protocol", "ProtocolRow"]

_CREATION_TOKEN = object()


@dataclass(slots=True, eq=False, repr=False)
class ProtocolRow:
    """One act's line in the protocol: which act, its number, and what it won.

    A row carries **no** copy of the act's name, participants or teachers. Those are
    read live from the Applications context every time the table is rendered, so a
    corrected surname shows up on the protocol and on the public page at once - which
    is what an organizer expects from a table of names, and the opposite of what a
    diploma needs (a diploma freezes its snapshot, because it is a document that was
    handed over).

    :attr:`number` is the number the act performed under, copied from the programme
    when the protocol was seeded. It is the row's own from then on: the programme's
    running order may be rearranged for a second stage or a repeat, and the protocol
    must keep saying what happened.

    :attr:`award` is ``None`` while the jury has not decided, and that stays a legal
    state - an act that did not appear has a row and no result.
    """

    _id: uuid.UUID
    _submission_id: uuid.UUID
    _number: int = 0
    _award: AwardKind | None = None

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def submission_id(self) -> uuid.UUID:
        return self._submission_id

    @property
    def number(self) -> int:
        """The number this act performed under."""
        return self._number

    @property
    def award(self) -> AwardKind | None:
        """What the jury awarded, or ``None`` while it has not decided."""
        return self._award

    @property
    def is_decided(self) -> bool:
        return self._award is not None

    def award_to(self, award: AwardKind | None) -> None:
        """Set (or clear) the result. Only the aggregate may call this."""
        self._award = award

    def assign_number(self, number: int) -> None:
        """Set this row's number. Only the aggregate may call this."""
        self._number = number

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ProtocolRow) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        award = self._award.value if self._award is not None else None
        return f"ProtocolRow(id={self._id!r}, number={self._number}, award={award!r})"


@dataclass(slots=True, eq=False, repr=False)
class Protocol:
    """The Protocol aggregate root - one nomination's results, for one competition.

    Scoped to a competition **and** a nomination, because that is how a jury sits and
    how results are announced: "итоги по вокалу" is a document, "итоги фестиваля" is a
    ceremony. One nomination has exactly one protocol; the repository enforces it.
    Equality is by id.
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _competition_id: uuid.UUID
    _nomination_id: uuid.UUID
    _name: ProtocolName
    _created_at: datetime
    _updated_at: datetime
    _status: ProtocolStatus = ProtocolStatus.DRAFT
    _rows: list[ProtocolRow] = field(default_factory=list)
    #: Which columns the published page shows. Empty means the safe default set.
    _public_columns: tuple[ProtocolColumn, ...] = ()
    #: Minted at the first publication and permanent from then on.
    _slug: PublicSlug | None = None
    #: How many times these results have been published. 0 while still a draft, so
    #: "ревизия 2" is unambiguously a correction of something people have seen.
    _revision: int = 0
    _published_at: datetime | None = None
    #: The aggregate version the current revision was published at - the pre-image
    #: :attr:`has_unpublished_changes` compares against, so no edit path can forget to
    #: raise a dirty flag.
    _published_version: int = 0
    #: The revision that is currently public: the verdict as it was published, frozen.
    #: ``None`` while never published. This is what the public page renders from, which is
    #: why a jury may keep correcting the live rows without anything leaking.
    _published_snapshot: PublishedSnapshot | None = None
    #: The programme this protocol's order and numbers were copied from. ``None`` for a
    #: protocol assembled by hand.
    _seeded_from_program_id: uuid.UUID | None = None
    _deleted_at: datetime | None = None
    _version: int = 1
    #: The version this aggregate was loaded at - the optimistic-concurrency pre-image
    #: the repository writes against. Transient (never persisted).
    _initial_version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise InvalidProtocolDataError("Protocol must be created via Protocol.create() or Protocol.rehydrate().")

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        protocol_id: uuid.UUID,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
        name: ProtocolName,
        now: datetime,
        public_columns: Sequence[ProtocolColumn] = (),
    ) -> Protocol:
        """Create an empty draft protocol. Rows are seeded or added afterwards."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=protocol_id,
            _competition_id=competition_id,
            _nomination_id=nomination_id,
            _name=name,
            _created_at=now,
            _updated_at=now,
            _public_columns=tuple(public_columns),
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        protocol_id: uuid.UUID,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
        name: ProtocolName,
        created_at: datetime,
        updated_at: datetime,
        status: ProtocolStatus = ProtocolStatus.DRAFT,
        rows: Sequence[ProtocolRow] = (),
        public_columns: Sequence[ProtocolColumn] = (),
        slug: PublicSlug | None = None,
        revision: int = 0,
        published_at: datetime | None = None,
        published_version: int = 0,
        published_snapshot: PublishedSnapshot | None = None,
        seeded_from_program_id: uuid.UUID | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> Protocol:
        """Reconstruct the aggregate from persistence (no re-validation)."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=protocol_id,
            _competition_id=competition_id,
            _nomination_id=nomination_id,
            _name=name,
            _created_at=created_at,
            _updated_at=updated_at,
            _status=status,
            _rows=list(rows),
            _public_columns=tuple(public_columns),
            _slug=slug,
            _revision=revision,
            _published_at=published_at,
            _published_version=published_version,
            _published_snapshot=published_snapshot,
            _seeded_from_program_id=seeded_from_program_id,
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
    def nomination_id(self) -> uuid.UUID:
        return self._nomination_id

    @property
    def name(self) -> ProtocolName:
        return self._name

    @property
    def status(self) -> ProtocolStatus:
        return self._status

    @property
    def is_published(self) -> bool:
        return self._status is ProtocolStatus.PUBLISHED

    @property
    def rows(self) -> tuple[ProtocolRow, ...]:
        """The protocol, in performance order."""
        return tuple(self._rows)

    @property
    def submission_ids(self) -> tuple[uuid.UUID, ...]:
        """The acts already in this protocol, in protocol order."""
        return tuple(row.submission_id for row in self._rows)

    @property
    def decided_rows(self) -> tuple[ProtocolRow, ...]:
        """The rows the jury has actually awarded something.

        What publication acts on: these are the rows that become a diploma degree and
        a letter. A row left blank is published as a blank line and issues nothing.
        """
        return tuple(row for row in self._rows if row.is_decided)

    @property
    def public_columns(self) -> tuple[ProtocolColumn, ...]:
        """The columns the published page shows, in canonical order.

        Never empty: a protocol published without a choice shows
        :data:`~apps.results.domain.value_objects.DEFAULT_PUBLIC_COLUMNS`, so there is
        no state in which "no columns were chosen" has to be handled downstream - and
        no way for a blank selection to be read as "show everything".
        """
        return self._public_columns or DEFAULT_PUBLIC_COLUMNS

    @property
    def slug(self) -> PublicSlug | None:
        """The permanent public slug, or ``None`` while never published."""
        return self._slug

    @property
    def revision(self) -> int:
        """How many times these results have been published (0 = never)."""
        return self._revision

    @property
    def published_at(self) -> datetime | None:
        """When the current revision was published, if any."""
        return self._published_at

    @property
    def published_version(self) -> int:
        """The aggregate version the current revision was published at."""
        return self._published_version

    @property
    def published_snapshot(self) -> PublishedSnapshot | None:
        """The verdict as it is currently public, or ``None`` if nothing is.

        The public page renders from this and never from :attr:`rows`, which is what makes
        a post-ceremony correction private until somebody publishes it.
        """
        return self._published_snapshot

    @property
    def seeded_from_program_id(self) -> uuid.UUID | None:
        return self._seeded_from_program_id

    @property
    def has_unpublished_changes(self) -> bool:
        """Whether the table has been edited since the revision that is out there.

        Read off the aggregate's own version rather than a flag, so no edit path can
        forget to set it: :meth:`publish` records the version it published, and any
        mutation afterwards moves past it.
        """
        return self.is_published and self._version > self._published_version

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

    def row(self, row_id: uuid.UUID) -> ProtocolRow:
        """Return one row, or raise :class:`ProtocolRowNotFoundError`."""
        for candidate in self._rows:
            if candidate.id == row_id:
                return candidate
        raise ProtocolRowNotFoundError("Этой строки нет в протоколе — обновите страницу.")

    def row_for_submission(self, submission_id: uuid.UUID) -> ProtocolRow | None:
        """The row for one act, or ``None`` if it has none."""
        for candidate in self._rows:
            if candidate.submission_id == submission_id:
                return candidate
        return None

    # ------------------------------------------------------------------
    # Protocol-level settings
    # ------------------------------------------------------------------

    def rename(self, name: ProtocolName, *, now: datetime) -> None:
        """Rename the protocol. Its slug, and therefore its link, is untouched."""
        self._name = name
        self._touch(now)

    def show_columns(self, columns: Sequence[ProtocolColumn], *, now: datetime) -> None:
        """Choose which columns the published page shows.

        Legal at any status. On a published protocol the change reaches nobody until
        the next :meth:`publish` - narrowing a public table is a correction like any
        other, and has to be as deliberate as the results themselves.
        """
        chosen = set(columns)
        self._public_columns = tuple(column for column in ProtocolColumn if column in chosen)
        self._touch(now)

    def seeded_from(self, program_id: uuid.UUID | None, *, now: datetime) -> None:
        """Record which programme this protocol's order was copied from."""
        self._seeded_from_program_id = program_id
        self._touch(now)

    # ------------------------------------------------------------------
    # Rows
    # ------------------------------------------------------------------

    def add_row(
        self,
        *,
        row_id: uuid.UUID,
        submission_id: uuid.UUID,
        now: datetime,
        number: int | None = None,
        award: AwardKind | None = None,
        position: int | None = None,
    ) -> ProtocolRow:
        """Give one act a line in the protocol (appended, or inserted at ``position``).

        ``number`` is the number the act performed under - the programme's, when the
        protocol was seeded from one. Without it the row takes the next free number,
        which is what a protocol assembled by hand wants.
        """
        if submission_id in self.submission_ids:
            raise PerformanceAlreadyInProtocolError("Это выступление уже есть в протоколе.")
        row = ProtocolRow(
            _id=row_id,
            _submission_id=submission_id,
            _number=number if number is not None else self._next_number(),
            _award=award,
        )
        self._insert(row, position)
        self._touch(now)
        return row

    def remove_row(self, row_id: uuid.UUID, *, now: datetime) -> None:
        """Drop one line - an act that never performed, a row added by mistake.

        The number goes with the row and is not handed to anyone else: a participant
        told "номер 7" must not find somebody else's result under номер 7.
        """
        row = self.row(row_id)
        self._rows.remove(row)
        self._touch(now)

    def reorder(self, ordered_row_ids: Sequence[uuid.UUID], *, now: datetime) -> None:
        """Rearrange the protocol's lines, leaving every number where it is.

        Takes the complete new order rather than a move instruction, so the request
        carries what the organizer sees and a stale client cannot half-apply a move.
        Numbers travel with their rows: the protocol reads 1, 2, 4, 3 when two acts
        swapped, because that is what happened on the day.
        """
        wanted = list(ordered_row_ids)
        if len(wanted) != len(set(wanted)) or set(wanted) != {row.id for row in self._rows}:
            raise ReorderMismatchError("Порядок задан неверно: список должен содержать все строки ровно по одному разу.")
        by_id = {row.id: row for row in self._rows}
        self._rows = [by_id[row_id] for row_id in wanted]
        self._touch(now)

    def renumber_sequentially(self, *, now: datetime) -> None:
        """Re-issue numbers 1..N along the current order.

        Offered as its own action, never as a side effect of a reorder: it rewrites
        numbers participants may already have been told.
        """
        for index, row in enumerate(self._rows, start=1):
            row.assign_number(index)
        self._touch(now)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def award_row(self, row_id: uuid.UUID, award: AwardKind | None, *, now: datetime) -> ProtocolRow:
        """Set (or clear) one act's result.

        Legal at **any** status and any number of times. Entering results is a live
        process - a jury revises a decision minutes after making it, and a published
        nomination's typo has to be fixable - so nothing here refuses a second write.
        On a published protocol the new value reaches nobody until the next
        :meth:`publish`; :attr:`has_unpublished_changes` is how a screen says so.
        """
        row = self.row(row_id)
        row.award_to(award)
        self._touch(now)
        return row

    def award_rows(self, awards: Iterable[tuple[uuid.UUID, AwardKind | None]], *, now: datetime) -> None:
        """Set several results at once - one save for a jury working down the list.

        Applied as a unit: an unknown row id rejects the whole batch rather than
        leaving half a nomination's results entered.
        """
        pairs = [(self.row(row_id), award) for row_id, award in awards]
        for row, award in pairs:
            row.award_to(award)
        self._touch(now)

    def clear_awards(self, *, now: datetime) -> None:
        """Clear every result (a rehearsal run, or results entered on the wrong day)."""
        for row in self._rows:
            row.award_to(None)
        self._touch(now)

    # ------------------------------------------------------------------
    # Publication
    # ------------------------------------------------------------------

    def publish(self, *, slug: PublicSlug, now: datetime) -> None:
        """Make the current results public, as a new revision.

        Four things happen at once, and they happen here so nothing can do one without the
        others: the current verdict is **frozen** into :attr:`published_snapshot`, the
        protocol becomes ``PUBLISHED``, its revision goes up, and (on the first publication
        only) it takes the permanent slug it will be reached by for the rest of its life.
        ``slug`` is minted by the caller and ignored on every later publication - a
        corrected protocol keeps its link, because a link that changed on correction would
        be a link nobody could keep.

        Freezing is what makes this method the gate it is meant to be. Awards stay editable
        afterwards, and those edits reach the live rows immediately and the public page not
        at all - so a jury re-reading its own decision at midnight is not broadcasting.

        Refuses only the empty case: publishing a protocol where no row has an award would
        announce results nobody decided and issue diplomas with nothing on them. Individual
        blanks are fine - an act that did not appear is a blank line.
        """
        if not self.decided_rows:
            raise AwardsIncompleteError("Публиковать нечего: в протоколе не проставлено ни одного результата.")
        if self._slug is None:
            self._slug = slug
        self._published_snapshot = PublishedSnapshot(
            name=str(self._name),
            columns=self.public_columns,
            results=tuple(PublishedResult(submission_id=row.submission_id, number=row.number, award=row.award) for row in self._rows),
        )
        self._status = ProtocolStatus.PUBLISHED
        self._revision += 1
        self._published_at = now
        self._touch(now)
        # After ``_touch``, so the recorded version *is* the published one and
        # ``has_unpublished_changes`` reads False until the next edit.
        self._published_version = self._version

    def unpublish(self, *, now: datetime) -> None:
        """Take the results back off the public page (a publication in error).

        The slug and the revision count stay: the link has existed and must not be re-minted
        for something else, and the revisions that were out there happened. The frozen
        snapshot is dropped, because there is no longer a public verdict for it to be. The
        link stops resolving, which is what makes this different from a correction - it says
        "these were not the results" rather than "these are".
        """
        self._status = ProtocolStatus.DRAFT
        self._published_at = None
        self._published_snapshot = None
        self._touch(now)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def delete(self, *, now: datetime) -> None:
        """Soft-delete the protocol; its public link stops resolving with it."""
        self._deleted_at = now
        self._touch(now)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _next_number(self) -> int:
        """One past the highest number in the protocol (numbers are never reused)."""
        return max((row.number for row in self._rows), default=0) + 1

    def _insert(self, row: ProtocolRow, position: int | None) -> None:
        """Place ``row`` at a 1-based ``position``, or append when it is ``None``."""
        if position is None:
            self._rows.append(row)
            return
        index = max(0, min(len(self._rows), position - 1))
        self._rows.insert(index, row)

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Protocol) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Protocol(id={self._id!r}, name={str(self._name)!r}, rows={len(self._rows)}, revision={self._revision})"
