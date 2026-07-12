"""Query messages for the Teacher Directory bounded context.

Immutable, transport-only read requests. ``requested_by`` scopes every read to the
acting user's own directory (ownership is enforced in the handler).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GetTeacherDirectoryQuery", "GetTeacherQuery"]


@dataclass(frozen=True, slots=True)
class GetTeacherQuery:
    """Retrieve a single teacher the acting user owns."""

    requested_by: str
    teacher_id: str


@dataclass(frozen=True, slots=True)
class GetTeacherDirectoryQuery:
    """List the acting user's directory entries, optionally including archived ones."""

    requested_by: str
    include_archived: bool = False
