"""Query DTOs for the Applications (Competition Submission) bounded context.

Input shapes for read use cases. Framework-neutral, frozen, slotted dataclasses
carrying only primitives. The acting identity travels on each query so the read
use case can enforce the same owner/organizer visibility rules the commands do.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GetSubmissionHistoryQuery",
    "GetSubmissionQuery",
    "ListCompetitionSubmissionsQuery",
    "ListMySubmissionsQuery",
]


@dataclass(frozen=True, slots=True)
class GetSubmissionQuery:
    """Fetch one submission in full (owner or an authorized organizer may view)."""

    submission_id: str
    requested_by: str


@dataclass(frozen=True, slots=True)
class ListMySubmissionsQuery:
    """List the submissions owned by the current applicant."""

    applicant_id: str


@dataclass(frozen=True, slots=True)
class ListCompetitionSubmissionsQuery:
    """List all submissions for a competition (authorized organizer only)."""

    competition_id: str
    requested_by: str


@dataclass(frozen=True, slots=True)
class GetSubmissionHistoryQuery:
    """Fetch a submission's review history (owner or an authorized organizer may view)."""

    submission_id: str
    requested_by: str
