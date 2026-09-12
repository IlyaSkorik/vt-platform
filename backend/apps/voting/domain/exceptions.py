"""Domain error vocabulary for the Voting bounded context.

Each error carries a stable ``code`` that the presentation layer maps onto an
RFC 9457 Problem Details response (API-000 §8), so views never hand-assemble a
problem body from ad-hoc strings.
"""

from __future__ import annotations

__all__ = [
    "AlreadyVotedError",
    "BallotError",
    "BallotNotFoundError",
    "BallotNotOpenError",
    "InvalidBallotDataError",
    "NomineeNotFoundError",
    "NomineeWithdrawnError",
    "NotEnoughNomineesError",
    "SlugUnavailableError",
    "TooFewNomineesError",
    "TooManyVotesFromNetworkError",
    "VoteLimitReachedError",
    "VotingClosedError",
]


class BallotError(Exception):
    """Base class for Voting domain/application errors."""

    code = "ballot_error"


class InvalidBallotDataError(BallotError):
    """Raised when a value object rejects its input (blank title, bad window, ...)."""

    code = "invalid_ballot_data"


class BallotNotFoundError(BallotError):
    """Raised when a referenced ballot does not exist (or was deleted)."""

    code = "ballot_not_found"


class NomineeNotFoundError(BallotError):
    """Raised when a referenced nominee is not on this ballot."""

    code = "nominee_not_found"


class NomineeWithdrawnError(BallotError):
    """Raised when a vote is cast for a nominee who has been taken off the ballot."""

    code = "nominee_withdrawn"


class TooFewNomineesError(BallotError):
    """Raised when a ballot is opened with fewer than two nominees to choose between.

    A vote with one option is not a vote.
    """

    code = "too_few_nominees"


#: Kept as an alias while the name settles; both spell the same rule.
NotEnoughNomineesError = TooFewNomineesError


class BallotNotOpenError(BallotError):
    """Raised when a ballot is asked to do something its state does not allow."""

    code = "ballot_not_open"


class VotingClosedError(BallotError):
    """Raised when a vote arrives outside the ballot's voting window."""

    code = "voting_closed"


class AlreadyVotedError(BallotError):
    """Raised when this voter has already voted for this nominee in this window."""

    code = "already_voted"


class VoteLimitReachedError(BallotError):
    """Raised when this voter has spent every vote the ballot allows them."""

    code = "vote_limit_reached"


class TooManyVotesFromNetworkError(BallotError):
    """Raised when one network has cast implausibly many votes in this window.

    A soft brake rather than an accusation: a hall shares one NAT, so the ceiling
    is high and the refusal is temporary.
    """

    code = "too_many_votes_from_network"


class SlugUnavailableError(BallotError):
    """Raised when a free public slug could not be minted."""

    code = "slug_unavailable"
