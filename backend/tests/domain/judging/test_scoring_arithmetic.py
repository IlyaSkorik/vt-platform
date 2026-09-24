"""The arithmetic a festival is decided by.

These are the tests that matter most in the Judging context. Everything else — who may
press what, which screen shows which column — is recoverable from a bug report; a panel
that averaged wrongly hands out the wrong award at a ceremony and nobody finds out.

Three properties are asserted throughout: the numbers are exact (no binary floats), the
awkward panel sizes behave (a judge missing, a three-person panel asked to drop two
marks), and a score that falls outside every band earns nothing rather than something.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from apps.judging.domain.exceptions import InvalidJudgingDataError
from apps.judging.domain.value_objects import (
    AggregationMethod,
    AwardScale,
    AwardTier,
    CriteriaScope,
    CriteriaSet,
    Criterion,
    ScoringRules,
    TallyDimension,
    TallyScope,
)


def criterion(name: str, *, maximum: str = "10", weight: str = "1") -> Criterion:
    return Criterion(id=uuid.uuid4(), name=name, max_score=Decimal(maximum), weight=Decimal(weight))


class TestCriteria:
    def test_a_weighted_criterion_contributes_its_weight_times_its_mark(self) -> None:
        technique = criterion("Техника", maximum="10", weight="2")

        assert technique.contribution(Decimal("9")) == Decimal("18.00")

    def test_a_sheet_knows_the_most_one_judge_can_give(self) -> None:
        """The number an organizer sizes the award bands against."""
        sheet = CriteriaSet(
            scope=CriteriaScope.CATEGORY,
            target_id=uuid.uuid4(),
            criteria=(criterion("Техника", weight="2"), criterion("Артистизм", weight="1")),
        )

        assert sheet.max_total == Decimal("30.00")

    def test_a_criterion_out_of_zero_points_is_refused(self) -> None:
        with pytest.raises(InvalidJudgingDataError):
            criterion("Ничего", maximum="0")

    def test_the_same_criterion_cannot_appear_twice(self) -> None:
        duplicate = criterion("Техника")

        with pytest.raises(InvalidJudgingDataError):
            CriteriaSet(scope=CriteriaScope.CATEGORY, target_id=uuid.uuid4(), criteria=(duplicate, duplicate))


class TestAggregation:
    def test_an_average_stays_on_the_scale_of_one_sheet(self) -> None:
        """Which is why bands written for a ten-point sheet keep meaning what they say."""
        rules = ScoringRules(aggregation=AggregationMethod.AVERAGE)

        assert rules.aggregate([Decimal("9"), Decimal("8"), Decimal("10")]) == Decimal("9.00")

    def test_a_sum_moves_with_the_size_of_the_panel(self) -> None:
        rules = ScoringRules(aggregation=AggregationMethod.SUM)

        assert rules.aggregate([Decimal("9"), Decimal("8"), Decimal("10")]) == Decimal("27.00")

    def test_an_unjudged_act_has_no_score_rather_than_zero(self) -> None:
        """A zero is a panel that judged the act and thought little of it."""
        assert ScoringRules().aggregate([]) is None

    def test_dropping_both_ends_removes_the_outliers(self) -> None:
        rules = ScoringRules(drop_highest=True, drop_lowest=True)

        # 10 and 1 go; 9, 8 and 7 remain.
        assert rules.aggregate([Decimal("10"), Decimal("9"), Decimal("8"), Decimal("7"), Decimal("1")]) == Decimal("8.00")

    def test_nothing_is_dropped_when_too_few_marks_would_survive(self) -> None:
        """Dropping both ends of a three-judge panel leaves one mark deciding alone,
        which is the opposite of what the rule exists for."""
        rules = ScoringRules(drop_highest=True, drop_lowest=True)

        assert rules.aggregate([Decimal("10"), Decimal("8"), Decimal("6")]) == Decimal("8.00")

    def test_a_judge_who_did_not_score_does_not_dilute_the_average(self) -> None:
        """Four seats, three sheets: the average is of the three that exist."""
        rules = ScoringRules(aggregation=AggregationMethod.AVERAGE)

        assert rules.aggregate([Decimal("9"), Decimal("9"), Decimal("9")]) == Decimal("9.00")

    def test_the_arithmetic_is_exact(self) -> None:
        """9.1 + 9.2 + 9.3 over three is 9.20, not 9.199999999999999."""
        rules = ScoringRules(aggregation=AggregationMethod.AVERAGE)

        assert rules.aggregate([Decimal("9.1"), Decimal("9.2"), Decimal("9.3")]) == Decimal("9.20")


class TestAwardScale:
    @staticmethod
    def places() -> AwardScale:
        """The scale an organizer who hands out places writes."""
        return AwardScale(
            tiers=(
                AwardTier(code="FIRST", label="1 место", min_score=Decimal("9"), max_score=Decimal("10"), sort_order=0),
                AwardTier(code="SECOND", label="2 место", min_score=Decimal("8"), max_score=Decimal("8.99"), sort_order=1),
                AwardTier(code="THIRD", label="3 место", min_score=Decimal("7"), max_score=Decimal("7.99"), sort_order=2),
            )
        )

    def test_a_score_earns_the_tier_whose_band_covers_it(self) -> None:
        scale = self.places()

        assert scale.tier_for_score(Decimal("9.40")).label == "1 место"  # type: ignore[union-attr]
        assert scale.tier_for_score(Decimal("8.00")).label == "2 место"  # type: ignore[union-attr]

    def test_a_score_below_every_band_earns_nothing(self) -> None:
        """A festival that awards nothing under 7 has acts that finish with no award,
        and inventing one for them would be the platform overruling the organizer."""
        assert self.places().tier_for_score(Decimal("6.50")) is None

    def test_bands_are_inclusive_at_both_ends(self) -> None:
        scale = self.places()

        assert scale.tier_for_score(Decimal("9")).code == "FIRST"  # type: ignore[union-attr]
        assert scale.tier_for_score(Decimal("10")).code == "FIRST"  # type: ignore[union-attr]

    def test_an_open_top_band_has_no_ceiling(self) -> None:
        scale = AwardScale(tiers=(AwardTier(code="GRAND_PRIX", label="Гран-при", min_score=Decimal("95")),))

        assert scale.tier_for_score(Decimal("100")).code == "GRAND_PRIX"  # type: ignore[union-attr]

    def test_overlapping_bands_are_refused(self) -> None:
        """Two tiers claiming 90 points is not a preference, it is a scale that cannot
        answer the only question it is ever asked."""
        with pytest.raises(InvalidJudgingDataError):
            AwardScale(
                tiers=(
                    AwardTier(code="A", label="Первая", min_score=Decimal("85"), max_score=Decimal("95")),
                    AwardTier(code="B", label="Вторая", min_score=Decimal("90"), max_score=Decimal("99"), sort_order=1),
                )
            )

    def test_two_tiers_cannot_share_a_code(self) -> None:
        with pytest.raises(InvalidJudgingDataError):
            AwardScale(tiers=(AwardTier(code="FIRST", label="1 место"), AwardTier(code="FIRST", label="Первое", sort_order=1)))

    def test_the_default_scale_is_the_platforms_own_degrees_unbanded(self) -> None:
        """A festival that never opens the screen keeps rendering what it always did,
        and nothing is awarded by score until somebody writes the bands."""
        scale = AwardScale.default()

        assert scale.by_code("LAUREATE_I").label == "Лауреат I степени"  # type: ignore[union-attr]
        assert scale.is_banded is False
        assert scale.tier_for_score(Decimal("100")) is None

    def test_a_deleted_tier_is_simply_unknown(self) -> None:
        assert self.places().by_code("LAUREATE_I") is None


class TestTallyScope:
    def test_genre_is_always_part_of_the_scope(self) -> None:
        """A scope without it would put вокал and хореография on one sheet."""
        scope = TallyScope(dimensions=frozenset({TallyDimension.AGE_CATEGORY}))

        assert TallyDimension.CATEGORY in scope

    def test_the_axes_come_back_in_a_stable_human_order(self) -> None:
        scope = TallyScope(dimensions=frozenset({TallyDimension.PARTICIPATION_FORMAT, TallyDimension.AGE_CATEGORY}))

        assert scope.ordered() == (TallyDimension.CATEGORY, TallyDimension.AGE_CATEGORY, TallyDimension.PARTICIPATION_FORMAT)
