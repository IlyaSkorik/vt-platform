"""ACL over the Results context: every degree a jury can award.

The Diplomas context keeps a degree as an opaque string (see the note in
:mod:`apps.diplomas.domain.value_objects`), which is right for one diploma — its
degree is simply whatever the jury decided, and this context has no business
ranking it. The print package needs the other direction: *every* degree that could
be decided, so the organizer gets one overprint sheet per possible outcome.

That list is the Results context's closed vocabulary, read here rather than copied,
so a sheet and the protocol it will be filled in from can never name an award
differently.
"""

from __future__ import annotations

from apps.results.domain.value_objects import AwardKind

__all__ = ["awardable_degrees"]


def awardable_degrees() -> tuple[str, ...]:
    """Every degree as printed, in order of seniority (Гран-при first)."""
    return tuple(kind.label for kind in AwardKind)
