"""Query messages for the Participants bounded context.

A query is an intent to **read** state without mutating it (ARCH-001 §7.2, §7.4).
Like commands, queries are immutable, transport-only ``frozen``/``slots``
dataclasses carrying primitives; the matching handler resolves them against the
repository and shapes a result DTO. Kept separate from commands so the read side
never mutates.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GetParticipantQuery"]


@dataclass(frozen=True, slots=True)
class GetParticipantQuery:
    """Retrieve a single participant by its identifier."""

    participant_id: str
