"""Domain exceptions for the Judging bounded context.

One root per context (ARCH-001 §7.4) so the presentation edge can map the whole family
onto RFC 9457 problems in one place, and so a caller that does not care which rule was
broken can still catch the right thing.

Each error carries a stable ``code`` the presentation layer maps onto an RFC 9457
Problem Details response (API-000 §8, ARCH-001 §7.6), so views never hand-assemble a
problem body from ad-hoc strings.

Framework-free: nothing here knows about HTTP status codes. The mapping from these to
``409`` or ``422`` lives in :mod:`apps.judging.presentation.api.v1.problems`.
"""

from __future__ import annotations

__all__ = [
    "InvalidJudgingDataError",
    "JudgingError",
    "JuryMemberNotFoundError",
    "NotAssignedToGenreError",
    "OnlineJudgingDisabledError",
    "PerformanceClosedError",
    "ScorecardNotFoundError",
    "ScoringNotFoundError",
    "SetupNotFoundError",
    "UnknownCriterionError",
]


class JudgingError(Exception):
    """Base class for every Judging domain error."""

    code = "judging_error"


class InvalidJudgingDataError(JudgingError):
    """A value the domain refuses: a blank criterion, a negative score, a crossed band."""

    code = "invalid_judging_data"


class SetupNotFoundError(JudgingError):
    """No judging configuration exists for this competition yet."""

    code = "judging_setup_not_found"


class OnlineJudgingDisabledError(JudgingError):
    """The festival runs on protocols, so there is nothing here to score.

    Raised at the edge of every scoring use case rather than checked once at the
    screen: a tablet left open from last season must not be able to write marks into a
    festival whose organizer has since turned online judging off.
    """

    code = "online_judging_disabled"


class JuryMemberNotFoundError(JudgingError):
    """No such jury member on this competition's panel."""

    code = "jury_member_not_found"


class NotAssignedToGenreError(JudgingError):
    """This judge is not on the panel for the genre the act competes in.

    The fairness rule ARCH-001 §12.3 states as "jury may score only submissions in
    competitions they are assigned to", narrowed to the genre because that is how a
    panel is actually seated.
    """

    code = "not_assigned_to_genre"


class PerformanceClosedError(JudgingError):
    """The host has closed this act; its marks are frozen."""

    code = "performance_closed"


class ScoringNotFoundError(JudgingError):
    """This act has never been opened for scoring."""

    code = "scoring_not_found"


class ScorecardNotFoundError(JudgingError):
    """This judge has not scored this act."""

    code = "scorecard_not_found"


class UnknownCriterionError(JudgingError):
    """A mark was sent against a criterion the act's sheet does not have."""

    code = "unknown_criterion"
