"""``DiplomasAwardRegister`` - the write side of publishing, into the Diplomas context.

The one place the Results context reaches out and changes something in another context, so
it is worth being precise about what crosses the boundary: a list of
``(submission id, degree label)`` pairs, and nothing else. Results does not know what a
diploma number looks like, whether a PDF gets rendered, or which template a nomination
uses. It knows that a jury decided "Лауреат II степени" and that somebody owns the
document that says so.

Translation in one direction only: this adapter turns Diplomas' :class:`AwardOutcome` into
this context's :class:`AwardedDiploma`. Two nearly identical shapes on purpose - if
Diplomas ever adds a field about print runs or signatures, Results neither sees it nor has
to change.

Idempotence is inherited from the service behind it: publishing a corrected protocol
re-renders the same diplomas with the new degrees, keeping their numbers and the URLs
participants already hold.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from apps.diplomas.composition import build_diploma_award_service
from apps.results.application.interfaces import AwardedDiploma

__all__ = ["DiplomasAwardRegister"]


class DiplomasAwardRegister:
    """Concrete :class:`~apps.results.application.interfaces.AwardRegister`."""

    def record_awards(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
        awards: Sequence[tuple[uuid.UUID, str]],
        now: datetime,
    ) -> tuple[AwardedDiploma, ...]:
        """Write each result onto its diploma and issue the participant's copy."""
        outcomes = build_diploma_award_service().award(
            competition_id=competition_id,
            category_id=nomination_id,
            awards=list(awards),
            now=now,
        )
        return tuple(
            AwardedDiploma(
                submission_id=outcome.submission_id,
                number=outcome.number,
                degree=outcome.degree,
                created=outcome.created,
                file_url=outcome.file_url,
            )
            for outcome in outcomes
        )
