"""The rules the aggregates keep, and the tally that reads them.

The cases here are the ones that decide whether a festival day goes wrong quietly: a
criteria sheet edited mid-event, a mark sent for a criterion that no longer exists, a
judge correcting a sheet after the host has closed the act, and an act whose panel is
only half in.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.judging.domain.entities import JudgingSetup, JuryMember, PerformanceScoring, Scorecard
from apps.judging.domain.exceptions import (
    InvalidJudgingDataError,
    PerformanceClosedError,
    UnknownCriterionError,
)
from apps.judging.domain.services import PerformanceFacts, TallyService
from apps.judging.domain.value_objects import (
    AwardScale,
    AwardTier,
    CriteriaScope,
    CriteriaSet,
    Criterion,
    ScoringRules,
)

NOW = datetime(2026, 5, 16, 11, 0, tzinfo=UTC)


def criterion(name: str, *, maximum: str = "10", weight: str = "1") -> Criterion:
    return Criterion(id=uuid.uuid4(), name=name, max_score=Decimal(maximum), weight=Decimal(weight))


def setup_with(*, category_id: uuid.UUID, criteria: tuple[Criterion, ...], scale: AwardScale | None = None) -> JudgingSetup:
    setup = JudgingSetup.create(setup_id=uuid.uuid4(), competition_id=uuid.uuid4(), now=NOW)
    setup.replace_criteria(CriteriaSet(scope=CriteriaScope.CATEGORY, target_id=category_id, criteria=criteria), now=NOW)
    if scale is not None:
        setup.replace_award_scale(scale, now=NOW)
    return setup


def card_for(submission_id: uuid.UUID, member_id: uuid.UUID, *, competition_id: uuid.UUID | None = None) -> Scorecard:
    return Scorecard.create(
        scorecard_id=uuid.uuid4(),
        competition_id=competition_id or uuid.uuid4(),
        submission_id=submission_id,
        jury_member_id=member_id,
        now=NOW,
    )


class TestCriteriaResolution:
    def test_a_nomination_overrides_its_genre(self) -> None:
        """ "Эстрадный вокал" is judged on stage presence; "вокал" as a whole is not."""
        category_id, discipline_id = uuid.uuid4(), uuid.uuid4()
        setup = setup_with(category_id=category_id, criteria=(criterion("Интонация"),))
        setup.replace_criteria(
            CriteriaSet(scope=CriteriaScope.DISCIPLINE, target_id=discipline_id, criteria=(criterion("Сценография"),)),
            now=NOW,
        )

        resolved = setup.criteria_for(category_id=category_id, discipline_id=discipline_id)

        assert [item.name for item in resolved] == ["Сценография"]

    def test_an_override_replaces_rather_than_adds(self) -> None:
        """Merging would leave an organizer unable to drop an inherited criterion."""
        category_id, discipline_id = uuid.uuid4(), uuid.uuid4()
        setup = setup_with(category_id=category_id, criteria=(criterion("Интонация"), criterion("Ритм")))
        setup.replace_criteria(
            CriteriaSet(scope=CriteriaScope.DISCIPLINE, target_id=discipline_id, criteria=(criterion("Сценография"),)),
            now=NOW,
        )

        assert len(setup.criteria_for(category_id=category_id, discipline_id=discipline_id)) == 1

    def test_a_nomination_with_no_sheet_of_its_own_uses_its_genre(self) -> None:
        category_id = uuid.uuid4()
        setup = setup_with(category_id=category_id, criteria=(criterion("Интонация"),))

        assert [item.name for item in setup.criteria_for(category_id=category_id, discipline_id=uuid.uuid4())] == ["Интонация"]

    def test_a_genre_nobody_has_written_criteria_for_has_none(self) -> None:
        """A real answer, not an error: the caller decides whether that is a problem."""
        setup = JudgingSetup.create(setup_id=uuid.uuid4(), competition_id=uuid.uuid4(), now=NOW)

        assert setup.criteria_for(category_id=uuid.uuid4(), discipline_id=None) == ()

    def test_emptying_a_sheet_removes_it(self) -> None:
        category_id = uuid.uuid4()
        setup = setup_with(category_id=category_id, criteria=(criterion("Интонация"),))

        setup.replace_criteria(CriteriaSet(scope=CriteriaScope.CATEGORY, target_id=category_id, criteria=()), now=NOW)

        assert setup.criteria_sets == ()


class TestScorecard:
    def test_a_sheet_is_weighted_by_the_criteria_it_was_given(self) -> None:
        technique, artistry = criterion("Техника", weight="2"), criterion("Артистизм", weight="1")
        card = card_for(uuid.uuid4(), uuid.uuid4())

        card.submit(scores={technique.id: Decimal("9"), artistry.id: Decimal("8")}, criteria=(technique, artistry), comment=None, now=NOW)

        assert card.total((technique, artistry)) == Decimal("26.00")

    def test_a_line_left_blank_counts_as_zero(self) -> None:
        """Averaging only over the lines a judge filled would quietly reward leaving
        lines out."""
        technique, artistry = criterion("Техника"), criterion("Артистизм")
        card = card_for(uuid.uuid4(), uuid.uuid4())

        card.submit(scores={technique.id: Decimal("9")}, criteria=(technique, artistry), comment=None, now=NOW)

        assert card.total((technique, artistry)) == Decimal("9.00")

    def test_a_mark_above_the_criterions_ceiling_is_refused(self) -> None:
        """A tablet open since the criteria were edited is normal; a 12 out of 10 is not."""
        technique = criterion("Техника", maximum="10")
        card = card_for(uuid.uuid4(), uuid.uuid4())

        with pytest.raises(InvalidJudgingDataError):
            card.submit(scores={technique.id: Decimal("12")}, criteria=(technique,), comment=None, now=NOW)

    def test_a_mark_for_a_criterion_that_is_not_on_the_sheet_is_refused(self) -> None:
        technique = criterion("Техника")
        card = card_for(uuid.uuid4(), uuid.uuid4())

        with pytest.raises(UnknownCriterionError):
            card.submit(scores={uuid.uuid4(): Decimal("9")}, criteria=(technique,), comment=None, now=NOW)

    def test_a_genre_with_no_criteria_cannot_be_scored(self) -> None:
        card = card_for(uuid.uuid4(), uuid.uuid4())

        with pytest.raises(InvalidJudgingDataError):
            card.submit(scores={}, criteria=(), comment=None, now=NOW)

    def test_sending_again_replaces_the_sheet(self) -> None:
        """Which is what "правит, пока выступление не закрыто" is in practice."""
        technique = criterion("Техника")
        card = card_for(uuid.uuid4(), uuid.uuid4())

        card.submit(scores={technique.id: Decimal("7")}, criteria=(technique,), comment="ошибся", now=NOW)
        card.submit(scores={technique.id: Decimal("9")}, criteria=(technique,), comment=None, now=NOW)

        assert card.score_for(technique.id) == Decimal("9.00")
        assert card.comment is None

    def test_an_unsent_sheet_is_distinguishable_from_a_sent_one(self) -> None:
        card = card_for(uuid.uuid4(), uuid.uuid4())

        assert card.is_submitted is False


class TestPerformanceScoring:
    def test_a_closed_act_refuses_marks(self) -> None:
        scoring = PerformanceScoring.create(scoring_id=uuid.uuid4(), competition_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=NOW)
        scoring.open(now=NOW)
        scoring.close(now=NOW)

        with pytest.raises(PerformanceClosedError):
            scoring.require_open()

    def test_an_act_the_host_has_not_reached_refuses_marks(self) -> None:
        scoring = PerformanceScoring.create(scoring_id=uuid.uuid4(), competition_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=NOW)

        with pytest.raises(PerformanceClosedError):
            scoring.require_open()

    def test_re_opening_is_allowed(self) -> None:
        """A judge whose tablet dropped the connection is a normal event, and a platform
        that made closing final would be worked around by entering the mark as somebody
        else."""
        scoring = PerformanceScoring.create(scoring_id=uuid.uuid4(), competition_id=uuid.uuid4(), submission_id=uuid.uuid4(), now=NOW)
        scoring.open(now=NOW)
        scoring.close(now=NOW)

        scoring.open(now=NOW)

        assert scoring.is_open is True
        assert scoring.closed_at is None


class TestJuryMember:
    def test_a_member_with_no_genres_judges_the_whole_festival(self) -> None:
        """The common case for a small panel, and one an organizer should not have to
        tick off by hand."""
        member = JuryMember.create(member_id=uuid.uuid4(), competition_id=uuid.uuid4(), full_name="Иванова А.", email="a@b.ru", now=NOW)

        assert member.judges(uuid.uuid4()) is True

    def test_a_seated_member_judges_only_their_genres(self) -> None:
        vocals = uuid.uuid4()
        member = JuryMember.create(
            member_id=uuid.uuid4(),
            competition_id=uuid.uuid4(),
            full_name="Иванова А.",
            email="a@b.ru",
            now=NOW,
            category_ids=[vocals],
        )

        assert member.judges(vocals) is True
        assert member.judges(uuid.uuid4()) is False

    def test_an_invited_member_cannot_score_until_they_accept(self) -> None:
        member = JuryMember.create(
            member_id=uuid.uuid4(),
            competition_id=uuid.uuid4(),
            full_name="Иванова А.",
            email="a@b.ru",
            now=NOW,
            invitation_token="tok",
        )

        assert member.can_score is False

        member.accept(user_id=uuid.uuid4(), now=NOW)

        assert member.can_score is True
        assert member.invitation_token is None, "the link must not seat a second person"

    def test_a_revoked_member_cannot_score(self) -> None:
        member = JuryMember.create(member_id=uuid.uuid4(), competition_id=uuid.uuid4(), full_name="И.", email="a@b.ru", now=NOW)
        member.accept(user_id=uuid.uuid4(), now=NOW)

        member.revoke(now=NOW)

        assert member.can_score is False


class TestTally:
    @staticmethod
    def scale() -> AwardScale:
        return AwardScale(
            tiers=(
                AwardTier(code="FIRST", label="1 место", min_score=Decimal("9"), max_score=Decimal("10"), sort_order=0),
                AwardTier(code="SECOND", label="2 место", min_score=Decimal("8"), max_score=Decimal("8.99"), sort_order=1),
            )
        )

    def test_an_acts_score_becomes_the_award_its_band_names(self) -> None:
        category_id, submission_id = uuid.uuid4(), uuid.uuid4()
        technique = criterion("Техника")
        setup = setup_with(category_id=category_id, criteria=(technique,), scale=self.scale())
        cards = []
        for _ in range(3):
            card = card_for(submission_id, uuid.uuid4())
            card.submit(scores={technique.id: Decimal("9.5")}, criteria=(technique,), comment=None, now=NOW)
            cards.append(card)

        result = TallyService(setup).tally(
            facts=PerformanceFacts(submission_id=submission_id, category_id=category_id),
            scorecards=cards,
            expected_judges=3,
        )

        assert result.score == Decimal("9.50")
        assert result.award_label == "1 место"
        assert result.is_complete is True

    def test_an_act_missing_a_sheet_is_reckoned_but_not_complete(self) -> None:
        """What the hall's board reads as "2 из 3"."""
        category_id, submission_id = uuid.uuid4(), uuid.uuid4()
        technique = criterion("Техника")
        setup = setup_with(category_id=category_id, criteria=(technique,), scale=self.scale())
        cards = []
        for _ in range(2):
            card = card_for(submission_id, uuid.uuid4())
            card.submit(scores={technique.id: Decimal("8.5")}, criteria=(technique,), comment=None, now=NOW)
            cards.append(card)

        result = TallyService(setup).tally(
            facts=PerformanceFacts(submission_id=submission_id, category_id=category_id),
            scorecards=cards,
            expected_judges=3,
        )

        assert result.score == Decimal("8.50")
        assert result.submitted_count == 2
        assert result.is_complete is False

    def test_an_unjudged_act_has_no_score_and_no_award(self) -> None:
        category_id, submission_id = uuid.uuid4(), uuid.uuid4()
        setup = setup_with(category_id=category_id, criteria=(criterion("Техника"),), scale=self.scale())

        result = TallyService(setup).tally(
            facts=PerformanceFacts(submission_id=submission_id, category_id=category_id),
            scorecards=(),
            expected_judges=3,
        )

        assert result.score is None
        assert result.award_code is None

    def test_a_started_sheet_that_was_never_sent_does_not_count(self) -> None:
        """A judge mid-typing must not pull the act's average down."""
        category_id, submission_id = uuid.uuid4(), uuid.uuid4()
        technique = criterion("Техника")
        setup = setup_with(category_id=category_id, criteria=(technique,), scale=self.scale())
        sent = card_for(submission_id, uuid.uuid4())
        sent.submit(scores={technique.id: Decimal("9.5")}, criteria=(technique,), comment=None, now=NOW)
        unsent = card_for(submission_id, uuid.uuid4())

        result = TallyService(setup).tally(
            facts=PerformanceFacts(submission_id=submission_id, category_id=category_id),
            scorecards=(sent, unsent),
            expected_judges=2,
        )

        assert result.score == Decimal("9.50")

    def test_a_score_between_two_bands_earns_nothing(self) -> None:
        """8.995 falls above "2 место" and below "1 место" — the organizer's gap, and
        the platform's job is to report it rather than to round into one of them."""
        category_id, submission_id = uuid.uuid4(), uuid.uuid4()
        technique = criterion("Техника")
        setup = setup_with(category_id=category_id, criteria=(technique,), scale=self.scale())
        card = card_for(submission_id, uuid.uuid4())
        card.submit(scores={technique.id: Decimal("8.99")}, criteria=(technique,), comment=None, now=NOW)
        setup.change_scoring_rules(ScoringRules(), now=NOW)

        result = TallyService(setup).tally(
            facts=PerformanceFacts(submission_id=submission_id, category_id=category_id),
            scorecards=(card,),
            expected_judges=1,
        )

        assert result.score == Decimal("8.99")
        assert result.award_code == "SECOND"

    def test_acts_are_grouped_by_the_axes_the_festival_announces_by(self) -> None:
        from apps.judging.domain.value_objects import TallyDimension, TallyScope

        category_id = uuid.uuid4()
        juniors, seniors = uuid.uuid4(), uuid.uuid4()
        setup = setup_with(category_id=category_id, criteria=(criterion("Техника"),), scale=self.scale())
        setup.change_tally_scope(TallyScope(dimensions=frozenset({TallyDimension.AGE_CATEGORY})), now=NOW)
        facts = [
            PerformanceFacts(submission_id=uuid.uuid4(), category_id=category_id, age_category_id=juniors),
            PerformanceFacts(submission_id=uuid.uuid4(), category_id=category_id, age_category_id=seniors),
        ]

        groups = TallyService(setup).group(facts=facts, scorecards_by_submission={}, expected_by_submission={})

        assert len(groups) == 2, "eight-year-olds are not announced with sixteen-year-olds"

    def test_one_genre_is_one_sheet_when_nothing_else_is_separated(self) -> None:
        category_id = uuid.uuid4()
        setup = setup_with(category_id=category_id, criteria=(criterion("Техника"),), scale=self.scale())
        facts = [
            PerformanceFacts(submission_id=uuid.uuid4(), category_id=category_id, age_category_id=uuid.uuid4()),
            PerformanceFacts(submission_id=uuid.uuid4(), category_id=category_id, age_category_id=uuid.uuid4()),
        ]

        groups = TallyService(setup).group(facts=facts, scorecards_by_submission={}, expected_by_submission={})

        assert len(groups) == 1
