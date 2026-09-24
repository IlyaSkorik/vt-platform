"""ACL over the Judging context: every degree one festival can award.

The Diplomas context keeps a degree as an opaque string (see the note in
:mod:`apps.diplomas.domain.value_objects`), which is right for one diploma — its
degree is simply whatever the jury decided, and this context has no business
ranking it. The print package needs the other direction: *every* degree that could
be decided, so the organizer gets one overprint sheet per possible outcome.

That list is **per festival**, because the award scale is: one organizer prints
"Лауреат I степени" and another "1 место", and a print package that offered the
platform's defaults to both would give one of them a folder of sheets they will never
hand out. Read here rather than copied, so a sheet and the protocol it will be filled
in from can never name an award differently.

Falls back to the Results context's built-in degrees for a festival that never
configured a scale — which is what such a festival's protocols are rendering from too.
"""

from __future__ import annotations

import uuid

from apps.judging.infrastructure.repositories import DjangoJudgingSetupRepository
from apps.results.domain.value_objects import AwardKind

__all__ = ["awardable_degrees"]


def awardable_degrees(competition_id: uuid.UUID | None = None) -> tuple[str, ...]:
    """Every degree this festival can award, as printed, most senior first."""
    if competition_id is not None:
        setup = DjangoJudgingSetupRepository().get(competition_id)
        if setup is not None and setup.award_scale.tiers:
            return tuple(tier.label for tier in setup.award_scale.tiers)
    return tuple(kind.label for kind in AwardKind)
