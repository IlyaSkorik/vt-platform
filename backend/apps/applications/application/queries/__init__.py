"""Query use cases for the Applications bounded context.

Read-side operations returning DTOs. Each handler reads through the repository
port, enforces the same owner/organizer visibility rules the commands do, and
projects the aggregate into flat views - never exposing a domain entity.
"""

from __future__ import annotations

from .get_submission import GetSubmissionHandler, GetSubmissionHistoryHandler
from .list_submissions import (
    ListCompetitionSubmissionsHandler,
    ListMySubmissionsHandler,
)

__all__ = [
    "GetSubmissionHandler",
    "GetSubmissionHistoryHandler",
    "ListCompetitionSubmissionsHandler",
    "ListMySubmissionsHandler",
]
