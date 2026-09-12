"""The ``Ballot`` aggregate — what the audience is being asked, and about whom.

A ballot is **not** a view over a programme or over the accepted submissions. It
holds its own ordered :class:`BallotNominee` children, and each of those carries
its own display data: the name, the act, the city, the photograph. The link back
to a submission or a programme row is an optional id and nothing hangs off it.

That is the design decision the whole feature rests on. A festival that has not
moved onto the platform still needs an audience vote, so a ballot belongs to an
organization and its ``competition_id`` may be null. When the festival *is* here,
the nominee list is seeded from the programme in one step; when it is not, the
same list is typed in or imported from a spreadsheet. Everything downstream reads
the ballot's own rows and cannot tell which way they arrived — so there is one
feature here, not two.

Copies rather than references also mean the ballot survives its surroundings: a
submission reworked in another context, a programme deleted after the event, a
nomination renamed next season. The record of what the audience was asked must
not change afterwards, and the only way to guarantee that is to hold it.

**Votes are not part of this aggregate.** There are thousands of them and they are
append-only; loading them to accept one more would be absurd. They live in their
own table behind their own repository, and the only thing the aggregate keeps is
each nominee's running count, which the vote use case advances in the same
transaction as the insert.

Framework-free (no Django, no DRF, no clock, no IO): time always arrives as ``now``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from typing import Final

from .exceptions import (
    BallotNotOpenError,
    InvalidBallotDataError,
    NomineeNotFoundError,
    NomineeWithdrawnError,
    TooFewNomineesError,
    VotingClosedError,
)
from .value_objects import (
    BallotStatus,
    BallotTitle,
    Cooldown,
    NomineeText,
    PublicSlug,
    RevealPolicy,
    VoteLimit,
    VotingWindow,
)

__all__ = ["Ballot", "BallotNominee"]

#: Opaque capability token proving construction went through a factory.
_CREATION_TOKEN: Final = object()

#: A vote needs something to choose between.
_MINIMUM_NOMINEES: Final = 2


@dataclass(slots=True, eq=False, repr=False)
class BallotNominee:
    """One entry the audience may vote for, carrying its own card.

    ``title`` is who is being voted for ("Ансамбль «Ритм»"); ``subtitle`` is what
    they did ("«Калинка», хореограф И. Петрова"); ``city`` and ``photo`` fill out
    the card. ``number`` is the number the act was announced under, when there is
    one — an audience looks for the number the host just read out, not for a name
    they may not have caught.

    ``votes`` is a running count kept here rather than recomputed: a hall refreshing
    a scoreboard must not each time aggregate a table that the hall is also writing
    to. The votes themselves remain the record of truth, and the count can always be
    rebuilt from them.
    """

    _id: uuid.UUID
    _title: NomineeText
    _subtitle: NomineeText = field(default_factory=lambda: NomineeText(""))
    _city: NomineeText = field(default_factory=lambda: NomineeText(""))
    _photo: str | None = None
    _number: int | None = None
    _position: int = 0
    _withdrawn: bool = False
    _votes: int = 0
    #: Optional id-only links back to where this nominee came from. Set when the
    #: list was seeded from a programme; null when it was typed or imported.
    _submission_id: uuid.UUID | None = None
    _program_item_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if self._title.empty:
            raise InvalidBallotDataError("У номинанта должно быть название.")
        if self._number is not None and self._number < 0:
            raise InvalidBallotDataError("Номер выступления не может быть отрицательным.")

    def edit(
        self,
        *,
        title: NomineeText | None = None,
        subtitle: NomineeText | None = None,
        city: NomineeText | None = None,
        photo: str | None = None,
        number: int | None = None,
    ) -> None:
        """Correct the card. Allowed at any time — a typo is not a result."""
        if title is not None:
            if title.empty:
                raise InvalidBallotDataError("У номинанта должно быть название.")
            self._title = title
        if subtitle is not None:
            self._subtitle = subtitle
        if city is not None:
            self._city = city
        if photo is not None:
            self._photo = photo or None
        if number is not None:
            if number < 0:
                raise InvalidBallotDataError("Номер выступления не может быть отрицательным.")
            self._number = number

    def withdraw(self) -> None:
        """Take the nominee off the ballot without erasing them.

        Withdrawn, not deleted: the votes already cast for them happened, and a
        result that quietly loses a contestant is a result nobody can audit. They
        stop being votable and stay in the final table with the count they had.
        """
        self._withdrawn = True

    def reinstate(self) -> None:
        """Put a withdrawn nominee back (an organizer's mistaken removal)."""
        self._withdrawn = False

    def record_vote(self) -> None:
        """Advance the running count by one."""
        self._votes += 1

    def set_votes(self, votes: int) -> None:
        """Overwrite the count from the votes table (a recount)."""
        if votes < 0:
            raise InvalidBallotDataError("Число голосов не может быть отрицательным.")
        self._votes = votes

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def title(self) -> NomineeText:
        return self._title

    @property
    def subtitle(self) -> NomineeText:
        return self._subtitle

    @property
    def city(self) -> NomineeText:
        return self._city

    @property
    def photo(self) -> str | None:
        return self._photo

    @property
    def number(self) -> int | None:
        return self._number

    @property
    def position(self) -> int:
        return self._position

    @property
    def withdrawn(self) -> bool:
        return self._withdrawn

    @property
    def votes(self) -> int:
        return self._votes

    @property
    def submission_id(self) -> uuid.UUID | None:
        return self._submission_id

    @property
    def program_item_id(self) -> uuid.UUID | None:
        return self._program_item_id

    def _place(self, position: int) -> None:
        self._position = position

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BallotNominee):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"BallotNominee({self._title.value!r}, votes={self._votes})"


@dataclass(slots=True, eq=False, repr=False)
class Ballot:
    """One audience vote: its question, its nominees and the rules it runs under."""

    _token: InitVar[object]
    _id: uuid.UUID
    _organization_id: uuid.UUID
    _title: BallotTitle
    _slug: PublicSlug
    _status: BallotStatus
    _created_at: datetime
    _updated_at: datetime
    #: Null when the ballot stands on its own — a festival that has not moved onto
    #: the platform, which is the case this whole context exists to serve.
    _competition_id: uuid.UUID | None = None
    _description: str = ""
    _window: VotingWindow = field(default_factory=VotingWindow)
    _vote_limit: VoteLimit = field(default_factory=VoteLimit)
    _cooldown: Cooldown = field(default_factory=Cooldown)
    _reveal: RevealPolicy = RevealPolicy.AFTER_CLOSE
    _nominees: list[BallotNominee] = field(default_factory=list)
    _opened_at: datetime | None = None
    _closed_at: datetime | None = None
    _deleted_at: datetime | None = None
    _version: int = 1

    def __post_init__(self, _token: object) -> None:
        if _token is not _CREATION_TOKEN:
            raise InvalidBallotDataError("Ballot must be created via draft() or rehydrate().")
        self._renumber()

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def draft(
        cls,
        *,
        ballot_id: uuid.UUID,
        organization_id: uuid.UUID,
        title: BallotTitle,
        slug: PublicSlug,
        now: datetime,
        competition_id: uuid.UUID | None = None,
        description: str = "",
        window: VotingWindow | None = None,
        vote_limit: VoteLimit | None = None,
        cooldown: Cooldown | None = None,
        reveal: RevealPolicy = RevealPolicy.AFTER_CLOSE,
    ) -> Ballot:
        """Start a ballot. It is assembled in DRAFT and accepts no votes yet."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=ballot_id,
            _organization_id=organization_id,
            _title=title,
            _slug=slug,
            _status=BallotStatus.DRAFT,
            _created_at=now,
            _updated_at=now,
            _competition_id=competition_id,
            _description=description,
            _window=window or VotingWindow(),
            _vote_limit=vote_limit or VoteLimit(),
            _cooldown=cooldown or Cooldown(),
            _reveal=reveal,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        ballot_id: uuid.UUID,
        organization_id: uuid.UUID,
        title: BallotTitle,
        slug: PublicSlug,
        status: BallotStatus,
        created_at: datetime,
        updated_at: datetime,
        competition_id: uuid.UUID | None = None,
        description: str = "",
        window: VotingWindow | None = None,
        vote_limit: VoteLimit | None = None,
        cooldown: Cooldown | None = None,
        reveal: RevealPolicy = RevealPolicy.AFTER_CLOSE,
        nominees: Iterable[BallotNominee] = (),
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
        deleted_at: datetime | None = None,
        version: int = 1,
    ) -> Ballot:
        """Reconstruct from persistence: no validation, no events."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=ballot_id,
            _organization_id=organization_id,
            _title=title,
            _slug=slug,
            _status=status,
            _created_at=created_at,
            _updated_at=updated_at,
            _competition_id=competition_id,
            _description=description,
            _window=window or VotingWindow(),
            _vote_limit=vote_limit or VoteLimit(),
            _cooldown=cooldown or Cooldown(),
            _reveal=reveal,
            _nominees=list(nominees),
            _opened_at=opened_at,
            _closed_at=closed_at,
            _deleted_at=deleted_at,
            _version=version,
        )

    # ------------------------------------------------------------------
    # Assembling the list
    # ------------------------------------------------------------------

    def add_nominee(
        self,
        *,
        nominee_id: uuid.UUID,
        title: NomineeText,
        now: datetime,
        subtitle: NomineeText | None = None,
        city: NomineeText | None = None,
        photo: str | None = None,
        number: int | None = None,
        submission_id: uuid.UUID | None = None,
        program_item_id: uuid.UUID | None = None,
    ) -> BallotNominee:
        """Put another nominee at the end of the list.

        Allowed while the ballot is open, and deliberately so: an act added to the
        running order on the day has to be votable on the day. It is unfair to the
        latecomer rather than to the people already on the list, which is the
        organizer's call to make and not ours to refuse.
        """
        self._refuse_if_closed()
        nominee = BallotNominee(
            _id=nominee_id,
            _title=title,
            _subtitle=subtitle or NomineeText(""),
            _city=city or NomineeText(""),
            _photo=photo or None,
            _number=number,
            _submission_id=submission_id,
            _program_item_id=program_item_id,
        )
        self._nominees.append(nominee)
        self._renumber()
        self._touch(now)
        return nominee

    def remove_nominee(self, nominee_id: uuid.UUID, *, now: datetime) -> None:
        """Take a nominee off the ballot.

        Erased outright only while nobody has voted for them. Once a vote exists the
        removal becomes a withdrawal, because deleting the row would silently change
        a total that people have already seen.
        """
        nominee = self.nominee(nominee_id)
        self._refuse_if_closed()
        if nominee.votes > 0:
            nominee.withdraw()
        else:
            self._nominees.remove(nominee)
        self._renumber()
        self._touch(now)

    def reorder_nominees(self, order: Sequence[uuid.UUID], *, now: datetime) -> None:
        """Rearrange the list. ``order`` must name every nominee exactly once."""
        self._refuse_if_closed()
        by_id = {nominee.id: nominee for nominee in self._nominees}
        if len(order) != len(by_id) or set(order) != set(by_id):
            raise InvalidBallotDataError("Новый порядок должен перечислить каждого номинанта ровно один раз.")
        self._nominees = [by_id[nominee_id] for nominee_id in order]
        self._renumber()
        self._touch(now)

    def nominee(self, nominee_id: uuid.UUID) -> BallotNominee:
        """The nominee with this id, or :class:`NomineeNotFoundError`."""
        for candidate in self._nominees:
            if candidate.id == nominee_id:
                return candidate
        raise NomineeNotFoundError("Номинанта нет в этом голосовании.")

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def update(
        self,
        *,
        now: datetime,
        title: BallotTitle | None = None,
        description: str | None = None,
        window: VotingWindow | None = None,
        vote_limit: VoteLimit | None = None,
        cooldown: Cooldown | None = None,
        reveal: RevealPolicy | None = None,
    ) -> None:
        """Change the ballot's wording or its rules.

        The rules may be edited while it is open — an organizer who realises at
        eight o'clock that the vote should close at ten needs to say so — but not
        after it has closed, when they would be editing a result.
        """
        self._refuse_if_closed()
        if title is not None:
            self._title = title
        if description is not None:
            self._description = description.strip()
        if window is not None:
            self._window = window
        if vote_limit is not None:
            self._vote_limit = vote_limit
        if cooldown is not None:
            self._cooldown = cooldown
        if reveal is not None:
            self._reveal = reveal
        self._touch(now)

    # ------------------------------------------------------------------
    # The life of the vote
    # ------------------------------------------------------------------

    def open(self, *, now: datetime) -> None:
        """Start accepting votes."""
        if self._status is BallotStatus.CLOSED:
            raise BallotNotOpenError("Голосование уже завершено — его нельзя открыть заново.")
        if self._status is BallotStatus.OPEN:
            return
        if len(self.votable) < _MINIMUM_NOMINEES:
            raise TooFewNomineesError("Чтобы открыть голосование, нужно хотя бы два номинанта.")
        if self._window.has_expired(now):
            raise VotingClosedError("Срок голосования уже истёк — измените дату закрытия.")
        self._status = BallotStatus.OPEN
        self._opened_at = now
        self._touch(now)

    def close(self, *, now: datetime) -> None:
        """Stop accepting votes. One-way."""
        if self._status is BallotStatus.CLOSED:
            return
        self._status = BallotStatus.CLOSED
        self._closed_at = now
        self._touch(now)

    def is_accepting_votes(self, *, now: datetime) -> bool:
        """Whether a vote cast at ``now`` would be counted.

        The window is evaluated here rather than by a job that flips the status at
        midnight: a ballot whose closing time has passed is closed whether or not a
        worker was running, and a state that depends on a cron having fired is a
        state that lies after an outage.
        """
        return self._status is BallotStatus.OPEN and self._window.contains(now)

    def accept_vote_for(self, nominee_id: uuid.UUID, *, now: datetime) -> BallotNominee:
        """Check that this nominee can be voted for right now, and count the vote.

        Only the *aggregate's* half of accepting a vote: whether the ballot is open
        and the nominee is votable, plus the count. Whether this particular voter
        has already used their votes is a question about the votes table and is
        answered by the use case, which owns both halves of the transaction.
        """
        if not self.is_accepting_votes(now=now):
            raise VotingClosedError("Голосование сейчас не принимает голоса.")
        nominee = self.nominee(nominee_id)
        if nominee.withdrawn:
            raise NomineeWithdrawnError("Этот номинант снят с голосования.")
        nominee.record_vote()
        self._touch(now)
        return nominee

    def may_reveal_totals(self, *, now: datetime) -> bool:
        """Whether the public page may show the counts at ``now``."""
        if self._reveal is RevealPolicy.ALWAYS:
            return True
        if self._reveal is RevealPolicy.NEVER:
            return False
        return not self.is_accepting_votes(now=now) and self._status is not BallotStatus.DRAFT

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _renumber(self) -> None:
        for position, nominee in enumerate(self._nominees, start=1):
            nominee._place(position)

    def _refuse_if_closed(self) -> None:
        if self._status is BallotStatus.CLOSED:
            raise BallotNotOpenError("Голосование завершено — изменить его больше нельзя.")

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    # ------------------------------------------------------------------
    # Read-only state
    # ------------------------------------------------------------------

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def organization_id(self) -> uuid.UUID:
        return self._organization_id

    @property
    def competition_id(self) -> uuid.UUID | None:
        return self._competition_id

    @property
    def standalone(self) -> bool:
        """Whether this ballot runs without a festival on the platform."""
        return self._competition_id is None

    @property
    def title(self) -> BallotTitle:
        return self._title

    @property
    def slug(self) -> PublicSlug:
        return self._slug

    @property
    def status(self) -> BallotStatus:
        return self._status

    @property
    def description(self) -> str:
        return self._description

    @property
    def window(self) -> VotingWindow:
        return self._window

    @property
    def vote_limit(self) -> VoteLimit:
        return self._vote_limit

    @property
    def cooldown(self) -> Cooldown:
        return self._cooldown

    @property
    def reveal(self) -> RevealPolicy:
        return self._reveal

    @property
    def nominees(self) -> tuple[BallotNominee, ...]:
        return tuple(self._nominees)

    @property
    def votable(self) -> tuple[BallotNominee, ...]:
        """The nominees a vote may actually be cast for."""
        return tuple(nominee for nominee in self._nominees if not nominee.withdrawn)

    @property
    def total_votes(self) -> int:
        return sum(nominee.votes for nominee in self._nominees)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def opened_at(self) -> datetime | None:
        return self._opened_at

    @property
    def closed_at(self) -> datetime | None:
        return self._closed_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def version(self) -> int:
        return self._version

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ballot):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Ballot({self._title.value!r}, {self._status.value}, nominees={len(self._nominees)})"
