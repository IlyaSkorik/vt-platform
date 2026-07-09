
from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GetStaffInvitationQuery"]


@dataclass(frozen=True, slots=True)
class GetStaffInvitationQuery:
    """Look up a staff invitation by the raw token from the emailed link."""

    raw_token: str
