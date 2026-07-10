"""Application-layer exceptions for the Competitions bounded context.

The application layer's own error vocabulary, distinct from the domain's typed
errors (:mod:`apps.competitions.domain.exceptions`). A use case raises one of these
when *it* — not the domain — decides an operation cannot proceed, most commonly
when a repository getter returns ``None`` for an id the use case requires. Each
carries a stable :attr:`code` the presentation edge maps to an RFC 9457 Problem
Details response (ARCH-001 §7.6). Domain errors are mapped separately, by type.
"""

from __future__ import annotations

__all__ = ["ApplicationError", "CompetitionNotFoundError"]


class ApplicationError(Exception):
    """Base class for Competitions application-layer errors, carrying a stable ``code``."""

    code = "application_error"


class CompetitionNotFoundError(ApplicationError):
    """No competition exists for the requested id."""

    code = "competition_not_found"
