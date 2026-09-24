"""Domain services: turning a panel's sheets into results.

One stateless service, :class:`TallyService`, and it is the whole arithmetic of this
context in one place on purpose. The same numbers are read in four places — the
organizer's tally screen, the hall's board, the protocol that gets published, and the
diploma printed from it — and four renderings of "the score" that disagree by a tenth
of a point is the kind of thing that ends a festival's trust in a platform.

Nothing here touches a repository or a clock. It is given sheets and configuration and
returns numbers, which is what makes the awkward cases — a judge who did not score, a
genre with no criteria yet, a score that falls between two bands — testable without a
database.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from .entities import JudgingSetup, Scorecard
from .value_objects import AwardScale, Criterion, Score, ScoringRules, TallyDimension, TallyScope

__all__ = ["JudgeTotal", "PerformanceFacts", "PerformanceTally", "TallyGroup", "TallyKey", "TallyService"]


@dataclass(frozen=True, slots=True)
class JudgeTotal:
    """What one judge's sheet came to for one act."""

    jury_member_id: uuid.UUID
    total: Score
    #: Whether the sheet was actually sent. A card that exists but was never submitted
    #: is a judge mid-typing, and it must not pull an act's average down.
    submitted: bool = True


@dataclass(frozen=True, slots=True)
class PerformanceTally:
    """One act's arithmetic, from the individual sheets down to the award."""

    submission_id: uuid.UUID
    judge_totals: tuple[JudgeTotal, ...]
    #: ``None`` while nobody has sent a sheet — distinct from a score of zero, which is
    #: a panel that judged the act and thought little of it.
    score: Score | None
    #: The highest total one judge could have given, so a screen can print "87 из 100"
    #: without knowing what the criteria were.
    max_score: Score
    award_code: str | None
    award_label: str | None
    expected_judges: int

    @property
    def submitted_count(self) -> int:
        return sum(1 for item in self.judge_totals if item.submitted)

    @property
    def is_complete(self) -> bool:
        """Whether every judge seated for this act has sent a sheet."""
        return self.expected_judges > 0 and self.submitted_count >= self.expected_judges


@dataclass(frozen=True, slots=True)
class TallyKey:
    """What separates one group of results from another.

    Only the axes the festival actually reckons by are filled in; the rest stay
    ``None``, so two acts in the same genre land in the same group when the organizer
    has not asked for age to be separated and in different ones when they have.
    """

    category_id: uuid.UUID | None = None
    discipline_id: uuid.UUID | None = None
    age_category_id: uuid.UUID | None = None
    participation_format_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class TallyGroup:
    """One sheet of results: the acts reckoned together, best first."""

    key: TallyKey
    tallies: tuple[PerformanceTally, ...]


@dataclass(frozen=True, slots=True)
class PerformanceFacts:
    """What the tally needs to know about an act, read from other contexts.

    Deliberately ids and nothing else: the arithmetic does not need a title, and a
    service that takes names is one refactor away from putting them in a protocol.
    """

    submission_id: uuid.UUID
    category_id: uuid.UUID
    discipline_id: uuid.UUID | None = None
    age_category_id: uuid.UUID | None = None
    participation_format_id: uuid.UUID | None = None


class TallyService:
    """Scores, awards and grouping, derived from a festival's configuration."""

    def __init__(self, setup: JudgingSetup) -> None:
        self._setup = setup

    @property
    def rules(self) -> ScoringRules:
        return self._setup.scoring_rules

    @property
    def scale(self) -> AwardScale:
        return self._setup.award_scale

    @property
    def scope(self) -> TallyScope:
        return self._setup.tally_scope

    def criteria_for(self, facts: PerformanceFacts) -> tuple[Criterion, ...]:
        return self._setup.criteria_for(category_id=facts.category_id, discipline_id=facts.discipline_id)

    def tally(
        self,
        *,
        facts: PerformanceFacts,
        scorecards: Sequence[Scorecard],
        expected_judges: int,
    ) -> PerformanceTally:
        """One act's result from the sheets written for it."""
        criteria = self.criteria_for(facts)
        totals = tuple(
            JudgeTotal(
                jury_member_id=card.jury_member_id,
                total=card.total(criteria),
                submitted=card.is_submitted,
            )
            for card in sorted(scorecards, key=lambda card: str(card.jury_member_id))
        )
        submitted = [item.total for item in totals if item.submitted]
        score = self.rules.aggregate(submitted) if submitted else None
        tier = self.scale.tier_for_score(score) if score is not None else None
        max_score = Decimal(sum((item.contribution(item.max_score) for item in criteria), Decimal(0))).quantize(Decimal("0.01"))
        return PerformanceTally(
            submission_id=facts.submission_id,
            judge_totals=totals,
            score=score,
            max_score=max_score,
            award_code=tier.code if tier is not None else None,
            award_label=tier.label if tier is not None else None,
            expected_judges=expected_judges,
        )

    def key_for(self, facts: PerformanceFacts) -> TallyKey:
        """Which sheet of results this act belongs on."""
        scope = self.scope
        return TallyKey(
            category_id=facts.category_id if TallyDimension.CATEGORY in scope else None,
            discipline_id=facts.discipline_id if TallyDimension.DISCIPLINE in scope else None,
            age_category_id=facts.age_category_id if TallyDimension.AGE_CATEGORY in scope else None,
            participation_format_id=(facts.participation_format_id if TallyDimension.PARTICIPATION_FORMAT in scope else None),
        )

    def group(
        self,
        *,
        facts: Sequence[PerformanceFacts],
        scorecards_by_submission: Mapping[uuid.UUID, Sequence[Scorecard]],
        expected_by_submission: Mapping[uuid.UUID, int],
    ) -> tuple[TallyGroup, ...]:
        """Every act reckoned and laid out in the groups the festival announces by.

        Within a group, acts are ordered by score, best first, with the unjudged last.
        That ordering is for reading, not for deciding: awards here come from the bands
        alone, so two acts on 92 points both take the same tier and their order on the
        sheet says nothing about which was better.
        """
        buckets: dict[TallyKey, list[PerformanceTally]] = {}
        for item in facts:
            tally = self.tally(
                facts=item,
                scorecards=scorecards_by_submission.get(item.submission_id, ()),
                expected_judges=expected_by_submission.get(item.submission_id, 0),
            )
            buckets.setdefault(self.key_for(item), []).append(tally)
        return tuple(
            TallyGroup(key=key, tallies=tuple(sorted(items, key=_ranking, reverse=True)))
            for key, items in sorted(buckets.items(), key=lambda entry: _key_sort(entry[0]))
        )


def _ranking(tally: PerformanceTally) -> tuple[int, Score]:
    """Judged acts above unjudged ones, and higher scores above lower."""
    return (1, tally.score) if tally.score is not None else (0, Decimal(0))


def _key_sort(key: TallyKey) -> tuple[str, str, str, str]:
    return (
        str(key.category_id or ""),
        str(key.discipline_id or ""),
        str(key.age_category_id or ""),
        str(key.participation_format_id or ""),
    )
