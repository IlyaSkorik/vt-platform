"""``JudgingAwardVocabulary`` — what this festival's awards are called.

Reads the Judging context's configuration and nothing else. The Results context stores
an award as a code and has no opinion about its name, because the name is the
organizer's: one festival's ``LAUREATE_I`` reads "Лауреат I степени" and another's
reads "1 место", and both are correct.

Reads the repository rather than the Judging composition root on purpose. This is a
lookup on a render path — every protocol detail, every public page — and going through
a use case would pull a mail gateway and a protocol writer into a query for nine
strings. It also keeps the import graph acyclic: Judging writes into Results through
:mod:`apps.judging.infrastructure.acl.protocol_writer`, so Results must not reach back
into anything that imports it.

A festival that never opened the scale screen has no row, and that is not a failure:
the empty answer means "no scale configured", and the service falls back to the
platform's built-in degrees — which is exactly what such a festival is running on.
"""

from __future__ import annotations

import uuid

from apps.judging.infrastructure.repositories import DjangoJudgingSetupRepository
from apps.results.application.interfaces import AwardTierView

__all__ = ["JudgingAwardVocabulary"]


class JudgingAwardVocabulary:
    """Concrete :class:`~apps.results.application.interfaces.AwardVocabulary`."""

    def tiers(self, competition_id: uuid.UUID) -> tuple[AwardTierView, ...]:
        """This festival's award scale, most senior first."""
        setup = DjangoJudgingSetupRepository().get(competition_id)
        if setup is None:
            return ()
        return tuple(AwardTierView(code=tier.code, label=tier.label, seniority=index) for index, tier in enumerate(setup.award_scale.tiers))
