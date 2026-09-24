"""Domain events emitted by the Judging bounded context.

Past-tense business facts (DATA-003). The integration currency between contexts
(ARCH-001 §4.8). Framework-free.

Only the facts another context has a reason to act on are here. A criterion being
renamed is not one of them: nothing outside this context reads criteria, and an event
nobody subscribes to is a maintenance cost pretending to be an integration point.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

__all__ = [
    "JuryMemberAccepted",
    "JuryMemberInvited",
    "PerformanceClosed",
    "PerformanceOpened",
    "ScorecardSubmitted",
]


@dataclass(frozen=True, slots=True)
class JuryMemberInvited:
    """An organizer seated somebody on the panel and a link went out to them."""

    member_id: uuid.UUID
    competition_id: uuid.UUID
    email: str
    full_name: str
    invitation_token: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class JuryMemberAccepted:
    """An invited judge signed in and their account is now attached to the seat."""

    member_id: uuid.UUID
    competition_id: uuid.UUID
    user_id: uuid.UUID
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class PerformanceOpened:
    """The host put an act on stage; the panel may write."""

    competition_id: uuid.UUID
    submission_id: uuid.UUID
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class PerformanceClosed:
    """The host closed an act; marks are frozen and, under ``AFTER_CLOSE``, revealed."""

    competition_id: uuid.UUID
    submission_id: uuid.UUID
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ScorecardSubmitted:
    """One judge sent their sheet.

    Carries the total rather than the individual marks: what the audit log and the
    board need is "this judge gave this act 9.4", and the marks behind it stay in the
    card where a judge's working belongs.
    """

    competition_id: uuid.UUID
    submission_id: uuid.UUID
    jury_member_id: uuid.UUID
    total: Decimal
    occurred_at: datetime
