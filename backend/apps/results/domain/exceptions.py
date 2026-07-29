"""Domain error vocabulary for the Results bounded context.

Each error carries a stable ``code`` that the presentation layer maps onto an
RFC 9457 Problem Details response (API-000 §8, ARCH-001 §7.6), so views never
hand-assemble a problem body from ad-hoc strings.
"""

from __future__ import annotations

__all__ = [
    "AwardsIncompleteError",
    "InvalidProtocolDataError",
    "PerformanceAlreadyInProtocolError",
    "PerformanceNotAvailableError",
    "ProtocolAlreadyExistsError",
    "ProtocolError",
    "ProtocolNotFoundError",
    "ProtocolNotPublishedError",
    "ProtocolRowNotFoundError",
    "ReorderMismatchError",
    "SlugUnavailableError",
]


class ProtocolError(Exception):
    """Base class for Results domain/application errors."""

    code = "protocol_error"


class InvalidProtocolDataError(ProtocolError):
    """Raised when a value object rejects its input (blank name, unknown award, ...)."""

    code = "invalid_protocol_data"


class ProtocolNotFoundError(ProtocolError):
    """Raised when a referenced protocol does not exist (or was deleted)."""

    code = "protocol_not_found"


class ProtocolRowNotFoundError(ProtocolError):
    """Raised when a referenced row is not part of the protocol."""

    code = "protocol_row_not_found"


class ProtocolAlreadyExistsError(ProtocolError):
    """Raised when a second protocol is created for a nomination that has one.

    One nomination, one protocol: two would each be a partial account of the same
    results, and nothing downstream could say which one a diploma came from.
    """

    code = "protocol_already_exists"


class PerformanceAlreadyInProtocolError(ProtocolError):
    """Raised when an act is added twice to the same protocol.

    One act, one result. A second row for the same submission would let two awards be
    entered for it and only one of them reach the diploma.
    """

    code = "performance_already_in_protocol"


class PerformanceNotAvailableError(ProtocolError):
    """Raised when the act being added did not compete in this protocol's scope.

    Guards the protocol against rows for entries still under review, cancelled, or
    belonging to another nomination entirely - a result for an act that never
    performed is the one thing a protocol must not be able to say.
    """

    code = "performance_not_available"


class ReorderMismatchError(ProtocolError):
    """Raised when a reorder request is not a permutation of the protocol's rows."""

    code = "reorder_mismatch"


class AwardsIncompleteError(ProtocolError):
    """Raised when publication is asked for and no row has an award yet.

    Not a completeness rule: a protocol may legitimately be published with rows left
    blank (an act that did not appear). It only refuses the empty case, where
    publishing would announce results that nobody has decided and would issue
    diplomas with no degree on them.
    """

    code = "awards_incomplete"


class ProtocolNotPublishedError(ProtocolError):
    """Raised when something only a published protocol has is asked for."""

    code = "protocol_not_published"


class SlugUnavailableError(ProtocolError):
    """Raised when a public slug could not be minted (or collides with a live one)."""

    code = "slug_unavailable"
