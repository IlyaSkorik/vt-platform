"""Value objects for the Voting bounded context.

Immutable, identity-less concepts (DATA-001 §8), framework-free.

Identifiers are plain :class:`uuid.UUID` values rather than a wrapper class each:
this context holds its own ids and id-only references outward
(``organization_id``, ``competition_id``, ``submission_id``, ``program_item_id``),
and none of them carries behaviour worth a type. The value objects here are the
ones with actual rules — what a ballot may be called, how long it runs, how many
votes a person gets, how often they come back, and who is allowed to see the count.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final

from .exceptions import InvalidBallotDataError

__all__ = [
    "BALLOT_TITLE_MAX",
    "COOLDOWN_MAX_HOURS",
    "NOMINEE_FIELD_MAX",
    "VOTES_PER_VOTER_MAX",
    "BallotStatus",
    "BallotTitle",
    "Cooldown",
    "NomineeText",
    "PublicSlug",
    "RevealPolicy",
    "VoteLimit",
    "VotingWindow",
]

BALLOT_TITLE_MAX: Final = 200
NOMINEE_FIELD_MAX: Final = 200

#: The ceiling on how many nominees one person may back.
#:
#: Above roughly this many, "vote for your favourites" stops discriminating — a
#: ballot where everyone may pick fifteen of twenty entries produces a ranking of
#: noise. The number is a sanity bound, not a recommendation; most ballots use one.
VOTES_PER_VOTER_MAX: Final = 10

#: The longest a ballot may make someone wait before voting again (a fortnight).
COOLDOWN_MAX_HOURS: Final = 24 * 14

#: The public slug alphabet: no characters that can be misread for one another,
#: because these links are typed off posters and read aloud from stages.
_SLUG_ALPHABET: Final = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_SLUG_LENGTH: Final = 10
_SLUG_MIN_LENGTH: Final = 6
_SLUG_MAX_LENGTH: Final = 64


class BallotStatus(StrEnum):
    """Where a ballot is in its life.

    ``DRAFT`` is assembled and invisible; ``OPEN`` accepts votes within its window;
    ``CLOSED`` is final. Deliberately one-way past ``CLOSED``: a ballot that could
    be reopened is a result that can be revised after people have seen it.
    """

    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class RevealPolicy(StrEnum):
    """Who may see the running count, and when.

    ``AFTER_CLOSE`` is the default the organizer should usually want: a live
    scoreboard is itself an incentive to rig the thing it is showing, because it
    tells a would-be stuffer exactly how many votes they still need.
    """

    ALWAYS = "ALWAYS"
    AFTER_CLOSE = "AFTER_CLOSE"
    NEVER = "NEVER"


def _clean(value: str, *, maximum: int, what: str) -> str:
    text = " ".join(str(value).split()).strip()
    if not text:
        raise InvalidBallotDataError(f"{what} не может быть пустым.")
    if len(text) > maximum:
        raise InvalidBallotDataError(f"{what} — не длиннее {maximum} символов.")
    return text


@dataclass(frozen=True, slots=True)
class BallotTitle:
    """What the ballot is called — the heading on the voting page."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _clean(self.value, maximum=BALLOT_TITLE_MAX, what="Название голосования"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class NomineeText:
    """One line of a nominee's card: who they are, what they do, where from.

    Blank is allowed here and refused only where it matters (a nominee must have a
    title; what they performed is optional), so the same type serves every line of
    the card.
    """

    value: str

    def __post_init__(self) -> None:
        text = " ".join(str(self.value).split()).strip()
        if len(text) > NOMINEE_FIELD_MAX:
            raise InvalidBallotDataError(f"Поле номинанта — не длиннее {NOMINEE_FIELD_MAX} символов.")
        object.__setattr__(self, "value", text)

    @property
    def empty(self) -> bool:
        return not self.value

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PublicSlug:
    """The unguessable token in a voting URL (``/vote/AbX82K``).

    The slug *is* the credential: the voting page carries no authentication, so it
    is minted from a confusable-free alphabet with enough entropy that a link
    cannot be found by trying, and it is never derived from the ballot's title.

    Deliberately a copy of the Programs context's value object rather than an
    import of it: the two contexts share no domain edge (ARCH-001 §14), and a
    little duplication is cheaper than a dependency between them.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = str(self.value).strip()
        if not (_SLUG_MIN_LENGTH <= len(stripped) <= _SLUG_MAX_LENGTH):
            raise InvalidBallotDataError(f"Адрес ссылки — от {_SLUG_MIN_LENGTH} до {_SLUG_MAX_LENGTH} символов.")
        if any(character not in _SLUG_ALPHABET for character in stripped):
            raise InvalidBallotDataError("В адресе ссылки допустимы только однозначные латинские символы и цифры.")
        object.__setattr__(self, "value", stripped)

    @classmethod
    def generate(cls) -> PublicSlug:
        """Mint a fresh random slug (~57 bits of entropy at the default length)."""
        return cls("".join(secrets.choice(_SLUG_ALPHABET) for _ in range(_SLUG_LENGTH)))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class VotingWindow:
    """When the ballot accepts votes, if it is bounded at all.

    Both ends are optional. An organizer who will open and close the vote by hand
    from their phone at the side of the stage sets neither, and that is a perfectly
    good way to run it; the window exists for the ones who would rather it closed
    itself at midnight whether or not anybody remembered.
    """

    opens_at: datetime | None = None
    closes_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.opens_at is not None and self.closes_at is not None and self.closes_at <= self.opens_at:
            raise InvalidBallotDataError("Голосование должно закрываться позже, чем открывается.")

    def contains(self, moment: datetime) -> bool:
        """Whether ``moment`` falls inside the window."""
        if self.opens_at is not None and moment < self.opens_at:
            return False
        return not (self.closes_at is not None and moment >= self.closes_at)

    def has_expired(self, moment: datetime) -> bool:
        """Whether the window's far end is already behind ``moment``."""
        return self.closes_at is not None and moment >= self.closes_at


@dataclass(frozen=True, slots=True)
class VoteLimit:
    """How many nominees one voter may back."""

    value: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise InvalidBallotDataError("Число голосов должно быть целым.")
        if not (1 <= self.value <= VOTES_PER_VOTER_MAX):
            raise InvalidBallotDataError(f"Число голосов на человека — от 1 до {VOTES_PER_VOTER_MAX}.")


@dataclass(frozen=True, slots=True)
class Cooldown:
    """How long a voter waits before their votes are replenished.

    Zero means "once, for the whole ballot" — the ordinary audience award. A
    non-zero value turns the ballot into a repeating one ("once a day for a week"),
    which some festivals run on purpose to keep an online vote alive across a run.

    The window a given instant falls into is a :meth:`bucket` number, and that
    number is part of the uniqueness rule in the database. That is the whole
    mechanism: "one vote per person per period" is a unique index, not a query.
    """

    hours: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.hours, int) or isinstance(self.hours, bool):
            raise InvalidBallotDataError("Период повторного голосования должен быть целым числом часов.")
        if not (0 <= self.hours <= COOLDOWN_MAX_HOURS):
            raise InvalidBallotDataError(f"Период повторного голосования — от 0 до {COOLDOWN_MAX_HOURS} часов.")

    @property
    def repeating(self) -> bool:
        return self.hours > 0

    def bucket(self, moment: datetime) -> int:
        """Which repeat window ``moment`` belongs to.

        Always ``0`` for a one-shot ballot, so the same unique index serves both
        kinds and neither needs a special case anywhere else.
        """
        if not self.repeating:
            return 0
        return int(moment.timestamp() // int(timedelta(hours=self.hours).total_seconds()))
