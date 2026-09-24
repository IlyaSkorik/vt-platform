"""Django repository adapters for the Judging bounded context."""

from .django_repositories import (
    DjangoJudgingSetupRepository,
    DjangoJuryMemberRepository,
    DjangoPerformanceScoringRepository,
    DjangoScorecardRepository,
)

__all__ = [
    "DjangoJudgingSetupRepository",
    "DjangoJuryMemberRepository",
    "DjangoPerformanceScoringRepository",
    "DjangoScorecardRepository",
]
