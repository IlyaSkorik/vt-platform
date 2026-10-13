"""Domain error vocabulary for the Programs bounded context.

Each error carries a stable ``code`` that the presentation layer maps onto an
RFC 9457 Problem Details response (API-000 §8), so views never hand-assemble a
problem body from ad-hoc strings.
"""

from __future__ import annotations

__all__ = [
    "ExportUnavailableError",
    "InvalidProgramDataError",
    "ItemNotInProgramError",
    "PerformanceAlreadyInProgramError",
    "PerformanceNotAvailableError",
    "ProgramColumnNotFoundError",
    "ProgramConcurrencyError",
    "ProgramError",
    "ProgramItemNotFoundError",
    "ProgramNotFoundError",
    "ProgramNumbersFrozenError",
    "ProgramShareNotFoundError",
    "ReorderMismatchError",
    "RunningOrderNotControllableError",
    "SlugUnavailableError",
]


class ProgramError(Exception):
    """Base class for Programs domain/application errors."""

    code = "program_error"


class InvalidProgramDataError(ProgramError):
    """Raised when a value object rejects its input (blank name, bad duration, ...)."""

    code = "invalid_program_data"


class ProgramConcurrencyError(ProgramError):
    """Raised when the program moved on between being read and being written.

    Every write to a program rewrites the whole aggregate - root row, items, columns,
    links - from the copy it loaded. That is the right unit to save in and the wrong
    thing to do blindly: a write that read the program before somebody else's change
    landed puts every field back the way it found them. The start time set a second
    earlier is simply gone, and nothing anywhere reports that it happened.

    So the version the copy was read at is checked at the moment of writing. It is the
    same ``version`` the API already hands to every client - it was being incremented,
    stored and returned, and never once used to refuse anything.
    """

    code = "program_conflict"


class ProgramNotFoundError(ProgramError):
    """Raised when a referenced program does not exist (or was deleted)."""

    code = "program_not_found"


class ProgramItemNotFoundError(ProgramError):
    """Raised when a referenced item is not part of the program."""

    code = "program_item_not_found"


class ExportUnavailableError(ProgramError):
    """Raised when an export is asked for and no renderer is wired up.

    A configuration fault rather than a request fault - the caller did nothing wrong.
    """

    code = "export_unavailable"


class ProgramNumbersFrozenError(ProgramError):
    """Raised when a published programme is asked to rebuild itself from scratch.

    Regenerating replaces every slot, and with it every number. Once the programme has
    been published those numbers are out in the world - a participant has been told
    "вы номер 12" - so the generator refuses rather than quietly renumbering people.
    The way forward is the organizer's: rearrange by hand, or start a new programme.
    """

    code = "program_numbers_frozen"


class ProgramColumnNotFoundError(ProgramError):
    """Raised when a referenced custom column is not part of the program."""

    code = "program_column_not_found"


class RunningOrderNotControllableError(ProgramError):
    """Raised when a public link is used to drive the day but was not granted that right.

    Only the host's edition may mark an act as on stage or rearrange what is still to
    come; every other link is read-only, and says nothing about which it is.
    """

    code = "running_order_not_controllable"


class ProgramShareNotFoundError(ProgramError):
    """Raised when a referenced public share of a program does not exist."""

    code = "program_share_not_found"


class ItemNotInProgramError(ProgramError):
    """Raised when a share selects an item that the program does not contain."""

    code = "item_not_in_program"


class PerformanceAlreadyInProgramError(ProgramError):
    """Raised when an act is added twice to the same program.

    One act occupies one slot: a second slot for the same submission would double
    it in the running order and in every schedule computed from it.
    """

    code = "performance_already_in_program"


class PerformanceNotAvailableError(ProgramError):
    """Raised when the act being added is not a competing act of this competition.

    Guards the program against slots for entries that are still under review, were
    cancelled, or belong to another competition entirely.
    """

    code = "performance_not_available"


class ReorderMismatchError(ProgramError):
    """Raised when a reorder request is not a permutation of the program's items.

    Reordering may only rearrange what is already there - it can neither add nor
    drop a slot, so a request that omits or invents an id is rejected whole.
    """

    code = "reorder_mismatch"


class SlugUnavailableError(ProgramError):
    """Raised when a public slug could not be minted (or collides with a live one)."""

    code = "slug_unavailable"
