"""Business policies for the Organization bounded context.

Explicit, testable business rules expressed as immutable, injectable policies
(ARCH-001 §4.2, §13.4). Each is a frozen, slotted dataclass whose fields *are*
its configuration: nothing is read from Django settings, environment, or a file.
The composition root constructs a policy with the knobs it wants and hands it to
a use case / aggregate.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only. Methods that
reason about time take the current instant (``now``) as an argument rather than
reading a global clock, so policies stay deterministic and trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from .exceptions import PolicyConfigurationError

__all__ = ["InvitationExpiryPolicy"]

#: Default validity window for a staff invitation link (7 days).
_DEFAULT_INVITATION_TTL: Final = timedelta(days=7)


@dataclass(frozen=True, slots=True)
class InvitationExpiryPolicy:
    """Decides when a staff invitation link stops being acceptable.

    The single knob is :attr:`ttl` — how long after issuance an invitation stays
    valid. The aggregate stamps ``expires_at = issued_at + ttl`` at issuance and
    checks a presented ``now`` against it at acceptance.
    """

    ttl: timedelta = _DEFAULT_INVITATION_TTL

    def __post_init__(self) -> None:
        if self.ttl <= timedelta(0):
            raise PolicyConfigurationError(f"Invitation ttl must be a positive duration, got {self.ttl!r}.")

    def expires_at(self, issued_at: datetime) -> datetime:
        """The instant an invitation issued at ``issued_at`` expires."""
        return issued_at + self.ttl

    def is_expired(self, *, expires_at: datetime, now: datetime) -> bool:
        """Whether an invitation with ``expires_at`` has lapsed at ``now``."""
        return now >= expires_at
