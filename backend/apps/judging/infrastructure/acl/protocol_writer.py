"""``ResultsProtocolWriter`` — the one place Judging writes into another context.

Worth being precise about what crosses the boundary: a list of ``(submission id, award
code)`` pairs per genre, and nothing else. Judging does not know what a protocol row
looks like, whether the protocol has been published, or what the award will be called
on a diploma. It knows that an act scored 92.4 and that the festival's scale calls that
``LAUREATE_I``.

Nothing is published here. Writing an award into a protocol and announcing it are two
different acts, and the second one stays the organizer's deliberate press of a button.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from apps.results.composition import build_protocol_service

__all__ = ["ResultsProtocolWriter"]


class ResultsProtocolWriter:
    """Concrete :class:`~apps.judging.application.interfaces.ProtocolWriter`."""

    def apply_awards(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
        awards: Sequence[tuple[uuid.UUID, str | None]],
        now: datetime,
    ) -> int:
        """Write one genre's computed results onto its protocol.

        ``now`` is accepted and not forwarded: the Results context stamps its own
        aggregate from its own clock, and handing it a timestamp from here would let two
        contexts disagree about when a protocol changed. The parameter stays in the port
        because the port is written for callers, and a caller that has a clock should be
        able to say so.
        """
        return build_protocol_service().apply_awards_by_submission(
            competition_id=competition_id,
            nomination_id=nomination_id,
            awards=list(awards),
        )
