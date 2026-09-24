"""Aggregates of the Judging bounded context.

Four roots, and the split between them is the load-bearing decision in this file.

:class:`JudgingSetup` is the festival's configuration — criteria, scoring rules, the
award scale, what the hall's board shows. One per competition, written by an organizer
between events and read by everything else.

:class:`JuryMember` is one person on the panel and the genres they judge.

:class:`PerformanceScoring` is one act's state on the day: pending, open to the panel,
or closed by the host. :class:`Scorecard` is one judge's marks for one act.

Those last two could have been one aggregate — the rule "a card may only be written
while its act is open" is exactly the kind of invariant a single root is for. They are
apart because of what happens in a hall: five judges press send within the same second,
and a single root would make four of those writes lose an optimistic-concurrency race
and retry, on tablets, on venue wifi. So the state is its own small aggregate that the
host writes and everyone reads, each card is its own row its own judge owns, and the
"act is open" check is done by the use case that loads both. The cost is that the rule
lives one layer out from the data; the benefit is that a panel can score at all.

Framework-free (no Django, no DRF). Persistence lives in the infrastructure mappers.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from decimal import Decimal

from .exceptions import (
    InvalidJudgingDataError,
    PerformanceClosedError,
    UnknownCriterionError,
)
from .value_objects import (
    AwardScale,
    BoardSettings,
    CriteriaScope,
    CriteriaSet,
    Criterion,
    JuryMemberStatus,
    PerformanceScoringStatus,
    Score,
    ScoringRules,
    TallyScope,
)

__all__ = ["CriterionScore", "JudgingSetup", "JuryMember", "PerformanceScoring", "Scorecard"]

_CREATION_TOKEN = object()

_NAME_MAX = 200
_TITLE_MAX = 200
_COMMENT_MAX = 2000


def _guard(token: object, what: str) -> None:
    if token is not _CREATION_TOKEN:
        raise InvalidJudgingDataError(f"{what} must be created via create() or rehydrate().")


def _name(value: str, *, what: str, limit: int = _NAME_MAX) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise InvalidJudgingDataError(f"Укажите {what}.")
    if len(raw) > limit:
        raise InvalidJudgingDataError(f"{what.capitalize()} — не длиннее {limit} символов.")
    return raw


# ---------------------------------------------------------------------------
# The festival's judging configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True, eq=False, repr=False)
class JudgingSetup:
    """Everything an organizer decides before a single mark is given.

    One per competition, created on first read rather than at festival creation: a
    festival that never opens this screen should not carry a row saying it did, and
    every field here has a defensible default, so an absent setup and a freshly
    defaulted one mean the same thing.

    The award scale lives here even though protocols use it under both judging modes.
    It is judging configuration in the sense that matters — it is the vocabulary
    results are expressed in — and putting it anywhere else would mean two places to
    look for "what can this festival award".
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _competition_id: uuid.UUID
    _created_at: datetime
    _updated_at: datetime
    _award_scale: AwardScale = field(default_factory=AwardScale.default)
    _criteria_sets: tuple[CriteriaSet, ...] = ()
    _scoring_rules: ScoringRules = field(default_factory=ScoringRules)
    _tally_scope: TallyScope = field(default_factory=TallyScope.default)
    _board: BoardSettings = field(default_factory=BoardSettings)
    #: Minted the first time the board is switched on, and permanent from then on — a
    #: projector in a hall is pointed at a URL once, often the evening before.
    _board_slug: str | None = None
    _version: int = 1
    _initial_version: int = 1

    def __post_init__(self, _token: object) -> None:
        _guard(_token, "JudgingSetup")

    # -- factories ---------------------------------------------------------

    @classmethod
    def create(cls, *, setup_id: uuid.UUID, competition_id: uuid.UUID, now: datetime) -> JudgingSetup:
        """A festival's default judging configuration."""
        return cls(
            _token=_CREATION_TOKEN,
            _id=setup_id,
            _competition_id=competition_id,
            _created_at=now,
            _updated_at=now,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        setup_id: uuid.UUID,
        competition_id: uuid.UUID,
        created_at: datetime,
        updated_at: datetime,
        award_scale: AwardScale,
        criteria_sets: Sequence[CriteriaSet],
        scoring_rules: ScoringRules,
        tally_scope: TallyScope,
        board: BoardSettings,
        board_slug: str | None,
        version: int,
    ) -> JudgingSetup:
        setup = cls(
            _token=_CREATION_TOKEN,
            _id=setup_id,
            _competition_id=competition_id,
            _created_at=created_at,
            _updated_at=updated_at,
            _award_scale=award_scale,
            _criteria_sets=tuple(criteria_sets),
            _scoring_rules=scoring_rules,
            _tally_scope=tally_scope,
            _board=board,
            _board_slug=board_slug,
            _version=version,
        )
        setup._initial_version = version
        return setup

    # -- reads -------------------------------------------------------------

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def competition_id(self) -> uuid.UUID:
        return self._competition_id

    @property
    def award_scale(self) -> AwardScale:
        return self._award_scale

    @property
    def criteria_sets(self) -> tuple[CriteriaSet, ...]:
        return self._criteria_sets

    @property
    def scoring_rules(self) -> ScoringRules:
        return self._scoring_rules

    @property
    def tally_scope(self) -> TallyScope:
        return self._tally_scope

    @property
    def board(self) -> BoardSettings:
        return self._board

    @property
    def board_slug(self) -> str | None:
        return self._board_slug

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
    def initial_version(self) -> int:
        return self._initial_version

    def criteria_for(self, *, category_id: uuid.UUID, discipline_id: uuid.UUID | None) -> tuple[Criterion, ...]:
        """The sheet an act in this genre and nomination is judged on.

        The nomination's own set wins when there is one, and the genre's is used
        otherwise. An empty tuple is a real answer — a genre nobody has written
        criteria for yet — and the caller decides whether that is a problem.
        """
        if discipline_id is not None:
            override = self._set_for(CriteriaScope.DISCIPLINE, discipline_id)
            if override is not None and not override.is_empty:
                return override.criteria
        genre = self._set_for(CriteriaScope.CATEGORY, category_id)
        return genre.criteria if genre is not None else ()

    def max_total_for(self, *, category_id: uuid.UUID, discipline_id: uuid.UUID | None) -> Score:
        """The highest total one judge can give an act here."""
        criteria = self.criteria_for(category_id=category_id, discipline_id=discipline_id)
        return Decimal(sum((item.contribution(item.max_score) for item in criteria), Decimal(0))).quantize(Decimal("0.01"))

    def _set_for(self, scope: CriteriaScope, target_id: uuid.UUID) -> CriteriaSet | None:
        return next((item for item in self._criteria_sets if item.scope is scope and item.target_id == target_id), None)

    # -- writes ------------------------------------------------------------

    def replace_award_scale(self, scale: AwardScale, *, now: datetime) -> None:
        """Replace the whole scale.

        Wholesale rather than per-tier because that is how the screen edits it, and
        because the overlap rule is a property of the list, not of any one row.

        Nothing stops an organizer deleting a tier that has already been awarded. The
        protocol keeps the code it stored and renders its own label for it, so a
        published result does not change its name because a scale was tidied up.
        """
        self._award_scale = scale
        self._touch(now)

    def replace_criteria(self, criteria_set: CriteriaSet, *, now: datetime) -> None:
        """Replace one genre's or nomination's sheet, adding it if it had none."""
        others = tuple(item for item in self._criteria_sets if not (item.scope is criteria_set.scope and item.target_id == criteria_set.target_id))
        self._criteria_sets = (*others, criteria_set) if not criteria_set.is_empty else others
        self._touch(now)

    def drop_criteria(self, *, scope: CriteriaScope, target_id: uuid.UUID, now: datetime) -> None:
        """Forget a sheet — used when its genre or nomination is deleted."""
        remaining = tuple(item for item in self._criteria_sets if not (item.scope is scope and item.target_id == target_id))
        if remaining == self._criteria_sets:
            return
        self._criteria_sets = remaining
        self._touch(now)

    def change_scoring_rules(self, rules: ScoringRules, *, now: datetime) -> None:
        self._scoring_rules = rules
        self._touch(now)

    def change_tally_scope(self, scope: TallyScope, *, now: datetime) -> None:
        self._tally_scope = scope
        self._touch(now)

    def change_board(self, board: BoardSettings, *, now: datetime, slug: str | None = None) -> None:
        """Change what the hall sees, minting the board's permanent link on first use."""
        self._board = board
        if board.enabled and self._board_slug is None:
            if not slug:
                raise InvalidJudgingDataError("Не удалось создать ссылку на табло.")
            self._board_slug = slug
        self._touch(now)

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, JudgingSetup) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"JudgingSetup(id={self._id!r}, competition_id={self._competition_id!r}, version={self._version})"


# ---------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------


@dataclass(slots=True, eq=False, repr=False)
class JuryMember:
    """One person on a festival's jury, and the genres they were seated for.

    A jury member is *not* a user account: they are a named seat on this festival's
    panel that an account is attached to when the invitation is accepted. The
    distinction matters twice — an organizer types the panel into the programme booklet
    weeks before anybody logs in, and the same human judging two festivals is two
    memberships with two sets of genres.

    :attr:`user_id` is therefore ``None`` until acceptance, and scoring is refused
    until it is not.
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _competition_id: uuid.UUID
    _full_name: str
    _email: str
    _created_at: datetime
    _updated_at: datetime
    _status: JuryMemberStatus = JuryMemberStatus.INVITED
    _user_id: uuid.UUID | None = None
    #: Regalia as they go in the booklet: "Заслуженный артист России", "председатель".
    _title: str | None = None
    _is_chair: bool = False
    #: The genres this member judges. Empty means the whole festival — the common case
    #: for a small panel, and the one an organizer should not have to tick off by hand.
    _category_ids: tuple[uuid.UUID, ...] = ()
    _sort_order: int = 0
    #: The single-use token the invitation link carries. Cleared on acceptance so a
    #: forwarded e-mail cannot seat a second person on the panel.
    _invitation_token: str | None = None
    _invited_at: datetime | None = None
    _accepted_at: datetime | None = None
    _revoked_at: datetime | None = None
    _version: int = 1
    _initial_version: int = 1

    def __post_init__(self, _token: object) -> None:
        _guard(_token, "JuryMember")

    @classmethod
    def create(
        cls,
        *,
        member_id: uuid.UUID,
        competition_id: uuid.UUID,
        full_name: str,
        email: str,
        now: datetime,
        title: str | None = None,
        is_chair: bool = False,
        category_ids: Sequence[uuid.UUID] = (),
        sort_order: int = 0,
        invitation_token: str | None = None,
    ) -> JuryMember:
        member = cls(
            _token=_CREATION_TOKEN,
            _id=member_id,
            _competition_id=competition_id,
            _full_name=_name(full_name, what="имя члена жюри"),
            _email=_email(email),
            _created_at=now,
            _updated_at=now,
            _title=_optional(title, what="регалии", limit=_TITLE_MAX),
            _is_chair=bool(is_chair),
            _category_ids=_unique(category_ids),
            _sort_order=max(0, int(sort_order)),
            _invitation_token=invitation_token,
            _invited_at=now if invitation_token else None,
        )
        return member

    @classmethod
    def rehydrate(
        cls,
        *,
        member_id: uuid.UUID,
        competition_id: uuid.UUID,
        full_name: str,
        email: str,
        created_at: datetime,
        updated_at: datetime,
        status: JuryMemberStatus,
        user_id: uuid.UUID | None,
        title: str | None,
        is_chair: bool,
        category_ids: Sequence[uuid.UUID],
        sort_order: int,
        invitation_token: str | None,
        invited_at: datetime | None,
        accepted_at: datetime | None,
        revoked_at: datetime | None,
        version: int,
    ) -> JuryMember:
        member = cls(
            _token=_CREATION_TOKEN,
            _id=member_id,
            _competition_id=competition_id,
            _full_name=full_name,
            _email=email,
            _created_at=created_at,
            _updated_at=updated_at,
            _status=status,
            _user_id=user_id,
            _title=title,
            _is_chair=is_chair,
            _category_ids=tuple(category_ids),
            _sort_order=sort_order,
            _invitation_token=invitation_token,
            _invited_at=invited_at,
            _accepted_at=accepted_at,
            _revoked_at=revoked_at,
            _version=version,
        )
        member._initial_version = version
        return member

    # -- reads -------------------------------------------------------------

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def competition_id(self) -> uuid.UUID:
        return self._competition_id

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def email(self) -> str:
        return self._email

    @property
    def status(self) -> JuryMemberStatus:
        return self._status

    @property
    def user_id(self) -> uuid.UUID | None:
        return self._user_id

    @property
    def title(self) -> str | None:
        return self._title

    @property
    def is_chair(self) -> bool:
        return self._is_chair

    @property
    def category_ids(self) -> tuple[uuid.UUID, ...]:
        return self._category_ids

    @property
    def sort_order(self) -> int:
        return self._sort_order

    @property
    def invitation_token(self) -> str | None:
        return self._invitation_token

    @property
    def invited_at(self) -> datetime | None:
        return self._invited_at

    @property
    def accepted_at(self) -> datetime | None:
        return self._accepted_at

    @property
    def revoked_at(self) -> datetime | None:
        return self._revoked_at

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
    def initial_version(self) -> int:
        return self._initial_version

    @property
    def can_score(self) -> bool:
        """Whether this seat may write marks: accepted, with an account behind it."""
        return self._status is JuryMemberStatus.ACTIVE and self._user_id is not None

    def judges(self, category_id: uuid.UUID) -> bool:
        """Whether this member is seated for that genre (no genres means all of them)."""
        return not self._category_ids or category_id in self._category_ids

    # -- writes ------------------------------------------------------------

    def rename(self, *, full_name: str, title: str | None, now: datetime) -> None:
        self._full_name = _name(full_name, what="имя члена жюри")
        self._title = _optional(title, what="регалии", limit=_TITLE_MAX)
        self._touch(now)

    def change_email(self, email: str, *, now: datetime, invitation_token: str | None = None) -> None:
        """Correct the address. A pending invitation is re-issued against the new one.

        An accepted membership keeps its account: the address is contact information at
        that point, and re-inviting somebody who is already judging would lock them out
        mid-festival.
        """
        self._email = _email(email)
        if self._status is JuryMemberStatus.INVITED and invitation_token:
            self._invitation_token = invitation_token
            self._invited_at = now
        self._touch(now)

    def assign_to(self, category_ids: Sequence[uuid.UUID], *, now: datetime) -> None:
        """Replace the genres this member judges. Empty means the whole festival."""
        self._category_ids = _unique(category_ids)
        self._touch(now)

    def make_chair(self, *, is_chair: bool, now: datetime) -> None:
        self._is_chair = bool(is_chair)
        self._touch(now)

    def reorder(self, sort_order: int, *, now: datetime) -> None:
        self._sort_order = max(0, int(sort_order))
        self._touch(now)

    def reinvite(self, token: str, *, now: datetime) -> None:
        """Issue a fresh invitation, invalidating any link already sent."""
        if self._status is JuryMemberStatus.ACTIVE:
            raise InvalidJudgingDataError("Этот член жюри уже принял приглашение.")
        self._status = JuryMemberStatus.INVITED
        self._invitation_token = token
        self._invited_at = now
        self._revoked_at = None
        self._touch(now)

    def accept(self, *, user_id: uuid.UUID, now: datetime) -> None:
        """Attach the account that answered the invitation."""
        if self._status is JuryMemberStatus.REVOKED:
            raise InvalidJudgingDataError("Приглашение отозвано.")
        self._user_id = user_id
        self._status = JuryMemberStatus.ACTIVE
        self._accepted_at = now
        self._invitation_token = None
        self._touch(now)

    def revoke(self, *, now: datetime) -> None:
        """Take the seat away. Marks already given stay — they are what the jury decided."""
        self._status = JuryMemberStatus.REVOKED
        self._invitation_token = None
        self._revoked_at = now
        self._touch(now)

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, JuryMember) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"JuryMember(id={self._id!r}, name={self._full_name!r}, status={self._status.value})"


# ---------------------------------------------------------------------------
# One act on the day
# ---------------------------------------------------------------------------


@dataclass(slots=True, eq=False, repr=False)
class PerformanceScoring:
    """Whether one act is open to the panel, and the running order it sits in.

    Created the first time the host reaches the act rather than seeded for the whole
    programme: a festival that runs three of its five days on the platform should not
    carry two days of rows saying nothing happened.
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _competition_id: uuid.UUID
    _submission_id: uuid.UUID
    _created_at: datetime
    _updated_at: datetime
    _status: PerformanceScoringStatus = PerformanceScoringStatus.PENDING
    _opened_at: datetime | None = None
    _closed_at: datetime | None = None
    _version: int = 1
    _initial_version: int = 1

    def __post_init__(self, _token: object) -> None:
        _guard(_token, "PerformanceScoring")

    @classmethod
    def create(cls, *, scoring_id: uuid.UUID, competition_id: uuid.UUID, submission_id: uuid.UUID, now: datetime) -> PerformanceScoring:
        return cls(
            _token=_CREATION_TOKEN,
            _id=scoring_id,
            _competition_id=competition_id,
            _submission_id=submission_id,
            _created_at=now,
            _updated_at=now,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        scoring_id: uuid.UUID,
        competition_id: uuid.UUID,
        submission_id: uuid.UUID,
        created_at: datetime,
        updated_at: datetime,
        status: PerformanceScoringStatus,
        opened_at: datetime | None,
        closed_at: datetime | None,
        version: int,
    ) -> PerformanceScoring:
        scoring = cls(
            _token=_CREATION_TOKEN,
            _id=scoring_id,
            _competition_id=competition_id,
            _submission_id=submission_id,
            _created_at=created_at,
            _updated_at=updated_at,
            _status=status,
            _opened_at=opened_at,
            _closed_at=closed_at,
            _version=version,
        )
        scoring._initial_version = version
        return scoring

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def competition_id(self) -> uuid.UUID:
        return self._competition_id

    @property
    def submission_id(self) -> uuid.UUID:
        return self._submission_id

    @property
    def status(self) -> PerformanceScoringStatus:
        return self._status

    @property
    def opened_at(self) -> datetime | None:
        return self._opened_at

    @property
    def closed_at(self) -> datetime | None:
        return self._closed_at

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
    def initial_version(self) -> int:
        return self._initial_version

    @property
    def is_open(self) -> bool:
        return self._status is PerformanceScoringStatus.OPEN

    @property
    def is_closed(self) -> bool:
        return self._status is PerformanceScoringStatus.CLOSED

    def open(self, *, now: datetime) -> None:
        """Let the panel write. Re-opening a closed act is allowed — see the status docstring."""
        self._status = PerformanceScoringStatus.OPEN
        self._opened_at = self._opened_at or now
        self._closed_at = None
        self._touch(now)

    def close(self, *, now: datetime) -> None:
        """Freeze the marks. Under ``AFTER_CLOSE`` this is also when the hall sees them."""
        self._status = PerformanceScoringStatus.CLOSED
        self._closed_at = now
        self._touch(now)

    def require_open(self) -> None:
        """Raise unless marks may be written right now."""
        if self._status is not PerformanceScoringStatus.OPEN:
            raise PerformanceClosedError("Оценка этого выступления закрыта ведущим.")

    def _touch(self, now: datetime) -> None:
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PerformanceScoring) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"PerformanceScoring(submission_id={self._submission_id!r}, status={self._status.value})"


@dataclass(frozen=True, slots=True)
class CriterionScore:
    """One mark against one criterion."""

    criterion_id: uuid.UUID
    score: Score


@dataclass(slots=True, eq=False, repr=False)
class Scorecard:
    """One judge's marks for one act, plus whatever they wanted the organizer to know.

    The card is a *whole* submission: a judge fills the sheet and sends it, and a
    partially filled card is not a thing the panel or the arithmetic has any use for.
    Sending again replaces it, which is what "правит, пока выступление не закрыто"
    means in practice.

    :attr:`comment` is for the organizer and nobody else. It is not shown to the
    participant, not published with the protocol, and not on the hall's board — a judge
    who knows otherwise writes nothing worth reading.
    """

    _token: InitVar[object]
    _id: uuid.UUID
    _competition_id: uuid.UUID
    _submission_id: uuid.UUID
    _jury_member_id: uuid.UUID
    _created_at: datetime
    _updated_at: datetime
    _scores: tuple[CriterionScore, ...] = ()
    _comment: str | None = None
    _submitted_at: datetime | None = None
    _version: int = 1
    _initial_version: int = 1

    def __post_init__(self, _token: object) -> None:
        _guard(_token, "Scorecard")

    @classmethod
    def create(
        cls,
        *,
        scorecard_id: uuid.UUID,
        competition_id: uuid.UUID,
        submission_id: uuid.UUID,
        jury_member_id: uuid.UUID,
        now: datetime,
    ) -> Scorecard:
        return cls(
            _token=_CREATION_TOKEN,
            _id=scorecard_id,
            _competition_id=competition_id,
            _submission_id=submission_id,
            _jury_member_id=jury_member_id,
            _created_at=now,
            _updated_at=now,
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        scorecard_id: uuid.UUID,
        competition_id: uuid.UUID,
        submission_id: uuid.UUID,
        jury_member_id: uuid.UUID,
        created_at: datetime,
        updated_at: datetime,
        scores: Sequence[CriterionScore],
        comment: str | None,
        submitted_at: datetime | None,
        version: int,
    ) -> Scorecard:
        card = cls(
            _token=_CREATION_TOKEN,
            _id=scorecard_id,
            _competition_id=competition_id,
            _submission_id=submission_id,
            _jury_member_id=jury_member_id,
            _created_at=created_at,
            _updated_at=updated_at,
            _scores=tuple(scores),
            _comment=comment,
            _submitted_at=submitted_at,
            _version=version,
        )
        card._initial_version = version
        return card

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def competition_id(self) -> uuid.UUID:
        return self._competition_id

    @property
    def submission_id(self) -> uuid.UUID:
        return self._submission_id

    @property
    def jury_member_id(self) -> uuid.UUID:
        return self._jury_member_id

    @property
    def scores(self) -> tuple[CriterionScore, ...]:
        return self._scores

    @property
    def comment(self) -> str | None:
        return self._comment

    @property
    def submitted_at(self) -> datetime | None:
        return self._submitted_at

    @property
    def is_submitted(self) -> bool:
        return self._submitted_at is not None

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
    def initial_version(self) -> int:
        return self._initial_version

    def score_for(self, criterion_id: uuid.UUID) -> Score | None:
        return next((item.score for item in self._scores if item.criterion_id == criterion_id), None)

    def total(self, criteria: Sequence[Criterion]) -> Score:
        """This judge's number for the act, weighted by the sheet they were given.

        Criteria the card has no mark for count as zero rather than being skipped: a
        sheet sent with a line left blank is a judge saying nothing there, and
        averaging over the lines they did fill would quietly reward leaving lines out.
        """
        by_id = {item.criterion_id: item.score for item in self._scores}
        total = sum((criterion.contribution(by_id.get(criterion.id, Decimal(0))) for criterion in criteria), Decimal(0))
        return Decimal(total).quantize(Decimal("0.01"))

    def submit(
        self,
        *,
        scores: Mapping[uuid.UUID, Score],
        criteria: Sequence[Criterion],
        comment: str | None,
        now: datetime,
    ) -> None:
        """Replace the sheet wholesale.

        Every mark is checked against the criterion it claims and against that
        criterion's own ceiling, because a tablet that has been open since the criteria
        were edited is a normal thing and a 12 out of 10 is not.
        """
        allowed = {criterion.id: criterion for criterion in criteria}
        if not allowed:
            raise InvalidJudgingDataError("Для этого жанра ещё не заданы критерии оценки.")
        checked: list[CriterionScore] = []
        for criterion_id, raw in scores.items():
            criterion = allowed.get(criterion_id)
            if criterion is None:
                raise UnknownCriterionError("Оценка выставлена по критерию, которого нет в этом жанре.")
            score = Decimal(raw).quantize(Decimal("0.01"))
            if score < 0:
                raise InvalidJudgingDataError(f"«{criterion.name}»: балл не может быть отрицательным.")
            if score > criterion.max_score:
                raise InvalidJudgingDataError(f"«{criterion.name}»: максимум {criterion.max_score} балла(ов).")
            checked.append(CriterionScore(criterion_id=criterion_id, score=score))
        self._scores = tuple(sorted(checked, key=lambda item: str(item.criterion_id)))
        self._comment = _optional(comment, what="комментарий", limit=_COMMENT_MAX)
        self._submitted_at = now
        self._updated_at = now
        self._version += 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Scorecard) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Scorecard(submission_id={self._submission_id!r}, jury_member_id={self._jury_member_id!r})"


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------


def _optional(value: str | None, *, what: str, limit: int) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) > limit:
        raise InvalidJudgingDataError(f"{what.capitalize()} — не длиннее {limit} символов.")
    return raw


def _email(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw or raw.count("@") != 1 or raw.startswith("@") or raw.endswith("@"):
        raise InvalidJudgingDataError("Укажите корректный адрес почты члена жюри.")
    if len(raw) > 320:
        raise InvalidJudgingDataError("Адрес почты слишком длинный.")
    return raw


def _unique(ids: Iterable[uuid.UUID]) -> tuple[uuid.UUID, ...]:
    return tuple(dict.fromkeys(ids))
