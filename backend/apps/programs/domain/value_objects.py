"""Value objects for the Programs bounded context.

Immutable, identity-less concepts (DATA-001 §8), framework-free.

Identifiers are plain :class:`uuid.UUID` values rather than one wrapper class per
reference (the approach the Diplomas context takes): this context holds ids only -
its own, and ``competition_id`` / ``nomination_id`` / ``submission_id`` pointing at
other contexts - and none of them carry behaviour worth a type of their own. The
value objects here are the ones with actual rules: a program's name, an item's
title, the two kinds of duration, the item kind, and a public slug.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .exceptions import InvalidProgramDataError

__all__ = [
    "BUFFER_MAX_SECONDS",
    "DURATION_MAX_SECONDS",
    "ItemDuration",
    "ItemTitle",
    "ProgramItemKind",
    "ProgramName",
    "PublicSlug",
    "ShareName",
    "TimeBuffer",
]

_NAME_MAX: Final = 200
_TITLE_MAX: Final = 200

#: A single item may not be longer than a day - the sanity ceiling a real running
#: order can never legitimately cross.
DURATION_MAX_SECONDS: Final = 24 * 60 * 60

#: The buffer pads one performance slot; anything beyond an hour is a break, and a
#: break is an item of its own.
BUFFER_MAX_SECONDS: Final = 60 * 60

_SLUG_ALPHABET: Final = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_SLUG_LENGTH: Final = 10
_SLUG_MIN_LENGTH: Final = 6
_SLUG_MAX_LENGTH: Final = 64


class ProgramItemKind(StrEnum):
    """What a slot in the running order *is*.

    ``PERFORMANCE`` binds one competing act (a submission) and takes its length
    from it. Every other kind is a **standalone block**: it carries its own title
    and its own duration, and nothing outside this context needs to exist for it.

    ``BREAK`` is what the interface offers today ("Перерыв", "Обед", "Подготовка
    сцены"). ``OPENING``, ``AWARD``, ``MASTER_CLASS`` and ``TECHNICAL`` are already
    valid and already schedule correctly - they are the same shape, and listing them
    here is the point of the design: a new kind of block needs no new table, no
    migration and no change to the time calculation.
    """

    PERFORMANCE = "PERFORMANCE"
    BREAK = "BREAK"
    OPENING = "OPENING"
    AWARD = "AWARD"
    MASTER_CLASS = "MASTER_CLASS"
    TECHNICAL = "TECHNICAL"

    @property
    def binds_performance(self) -> bool:
        """Whether this kind references a competing act instead of carrying a title."""
        return self is ProgramItemKind.PERFORMANCE

    @property
    def takes_buffer(self) -> bool:
        """Whether the program's buffer pads this kind of slot.

        Only performances: the buffer exists to absorb applause, stage entry and
        exit between acts. A break already *is* slack, and padding it would silently
        stretch the very item the organizer sized by hand.
        """
        return self is ProgramItemKind.PERFORMANCE


@dataclass(frozen=True, slots=True)
class ProgramName:
    """A non-empty, length-bounded program name ("Вокал, 1 отделение")."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidProgramDataError("Program name must not be empty.")
        if len(stripped) > _NAME_MAX:
            raise InvalidProgramDataError(f"Program name must be at most {_NAME_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ShareName:
    """A non-empty, length-bounded name for a public share ("Программа звукорежиссёра")."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidProgramDataError("Public program name must not be empty.")
        if len(stripped) > _NAME_MAX:
            raise InvalidProgramDataError(f"Public program name must be at most {_NAME_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ItemTitle:
    """A non-empty, length-bounded title for a standalone block ("Обед")."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise InvalidProgramDataError("Program item title must not be empty.")
        if len(stripped) > _TITLE_MAX:
            raise InvalidProgramDataError(f"Program item title must be at most {_TITLE_MAX} characters.")
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ItemDuration:
    """How long a slot lasts, as a whole number of seconds.

    Stored as an :class:`int` (never a float) so accumulated schedules stay exact.
    Strictly positive: a slot of no length would occupy a position in the running
    order while moving no clock.
    """

    seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.seconds, int) or isinstance(self.seconds, bool):
            raise InvalidProgramDataError(f"Duration seconds must be an int, got {type(self.seconds)!r}.")
        if self.seconds <= 0:
            raise InvalidProgramDataError(f"Duration must be positive, got {self.seconds} seconds.")
        if self.seconds > DURATION_MAX_SECONDS:
            raise InvalidProgramDataError(f"Duration must be at most {DURATION_MAX_SECONDS} seconds.")

    @classmethod
    def of(cls, *, minutes: int = 0, seconds: int = 0) -> ItemDuration:
        """Build a duration from minutes and/or seconds."""
        return cls(seconds=minutes * 60 + seconds)

    def __str__(self) -> str:
        minutes, seconds = divmod(self.seconds, 60)
        return f"{minutes}:{seconds:02d}"


@dataclass(frozen=True, slots=True)
class TimeBuffer:
    """The padding added to every performance slot when the schedule is computed.

    A program-level setting (30 seconds, 45 seconds, a minute, ...) that **never
    changes an act's own duration** - it only widens the slot the act sits in, so
    the same act keeps its declared length everywhere else in the platform.
    """

    seconds: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.seconds, int) or isinstance(self.seconds, bool):
            raise InvalidProgramDataError(f"Buffer seconds must be an int, got {type(self.seconds)!r}.")
        if self.seconds < 0:
            raise InvalidProgramDataError(f"Buffer must not be negative, got {self.seconds} seconds.")
        if self.seconds > BUFFER_MAX_SECONDS:
            raise InvalidProgramDataError(f"Buffer must be at most {BUFFER_MAX_SECONDS} seconds.")

    @classmethod
    def none(cls) -> TimeBuffer:
        """No padding at all."""
        return cls(seconds=0)

    def __str__(self) -> str:
        minutes, seconds = divmod(self.seconds, 60)
        return f"{minutes}:{seconds:02d}"


@dataclass(frozen=True, slots=True)
class PublicSlug:
    """The unguessable token in a public program URL (``/program/AbX82K``).

    The slug *is* the credential: a public program carries no authentication, so it
    is minted from a confusable-free alphabet with enough entropy that a link cannot
    be found by trying. Case-sensitive, and never derived from the program's name.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not (_SLUG_MIN_LENGTH <= len(stripped) <= _SLUG_MAX_LENGTH):
            raise InvalidProgramDataError(f"Slug must be {_SLUG_MIN_LENGTH}-{_SLUG_MAX_LENGTH} characters, got {len(stripped)}.")
        if any(char not in _SLUG_ALPHABET for char in stripped):
            raise InvalidProgramDataError("Slug must contain only unambiguous URL-safe characters.")
        object.__setattr__(self, "value", stripped)

    @classmethod
    def generate(cls) -> PublicSlug:
        """Mint a fresh random slug (~57 bits of entropy at the default length)."""
        return cls("".join(secrets.choice(_SLUG_ALPHABET) for _ in range(_SLUG_LENGTH)))

    def __str__(self) -> str:
        return self.value
