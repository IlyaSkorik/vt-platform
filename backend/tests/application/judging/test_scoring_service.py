"""A festival day, end to end, with nothing real behind it.

The cases here are the ones a hall actually produces: a judge who was never seated for
the genre, a tablet still showing an act the host has closed, a board configured to
keep marks quiet until the act is over, and a tally pushed into protocols that an
organizer has already corrected by hand.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from apps.judging.application.commands import (
    CloseScoringCommand,
    InviteJuryMemberCommand,
    OpenScoringCommand,
    SubmitScorecardCommand,
    UpdateAwardScaleCommand,
    UpdateBoardCommand,
    UpdateCriteriaCommand,
)
from apps.judging.application.interfaces import DirectoryNomination, DirectoryPerformance
from apps.judging.application.services import JudgingConfigurationService, ScoringService
from apps.judging.domain.exceptions import (
    JuryMemberNotFoundError,
    NotAssignedToGenreError,
    OnlineJudgingDisabledError,
    PerformanceClosedError,
    ScoringNotFoundError,
)

from .doubles import (
    FixedClock,
    InMemoryJudgingSetupRepository,
    InMemoryJuryMemberRepository,
    InMemoryPerformanceScoringRepository,
    InMemoryScorecardRepository,
    RecordingNotifier,
    RecordingProtocolWriter,
    ScriptedSlugFactory,
    ScriptedTokenFactory,
    SequentialUuids,
    StubCompetitionDirectory,
    StubPerformanceDirectory,
)

COMPETITION = uuid.uuid4()
VOCALS = uuid.uuid4()
DANCE = uuid.uuid4()
ACT_ONE = uuid.uuid4()
ACT_TWO = uuid.uuid4()


def performances() -> list[DirectoryPerformance]:
    return [
        DirectoryPerformance(
            submission_id=ACT_ONE,
            title="Журавли",
            category_id=VOCALS,
            number=1,
            category_name="Вокал",
            organization="ДШИ №3",
        ),
        DirectoryPerformance(submission_id=ACT_TWO, title="Вальс", category_id=DANCE, number=2, category_name="Хореография"),
    ]


class Festival:
    """One assembled festival, with the doubles left reachable for assertions."""

    def __init__(self, *, online: bool = True) -> None:
        self.setups = InMemoryJudgingSetupRepository()
        self.members = InMemoryJuryMemberRepository()
        self.scorings = InMemoryPerformanceScoringRepository()
        self.scorecards = InMemoryScorecardRepository()
        self.competitions = StubCompetitionDirectory(
            online=online,
            nominations=[
                DirectoryNomination(category_id=VOCALS, name="Вокал", sort_order=0),
                DirectoryNomination(category_id=DANCE, name="Хореография", sort_order=1),
            ],
        )
        self.performances = StubPerformanceDirectory(performances())
        self.clock = FixedClock()
        self.tokens = ScriptedTokenFactory()
        self.notifier = RecordingNotifier()
        self.protocols = RecordingProtocolWriter()
        self.config = JudgingConfigurationService(
            setups=self.setups,
            members=self.members,
            competitions=self.competitions,
            clock=self.clock,
            uuids=SequentialUuids(),
            slugs=ScriptedSlugFactory(),
            tokens=self.tokens,
            notifier=self.notifier,
        )
        self.scoring = ScoringService(
            setups=self.setups,
            members=self.members,
            scorings=self.scorings,
            scorecards=self.scorecards,
            competitions=self.competitions,
            performances=self.performances,
            clock=self.clock,
            uuids=SequentialUuids(),
            protocols=self.protocols,
        )

    def with_criteria(self, *, category_id: uuid.UUID = VOCALS) -> Festival:
        self.config.update_criteria(
            UpdateCriteriaCommand(
                competition_id=str(COMPETITION),
                scope="CATEGORY",
                target_id=str(category_id),
                criteria=[{"name": "Техника", "maxScore": "10", "weight": "1", "sortOrder": 0}],
            )
        )
        return self

    def with_places(self) -> Festival:
        self.config.update_award_scale(
            UpdateAwardScaleCommand(
                competition_id=str(COMPETITION),
                tiers=[
                    {"code": "FIRST", "label": "1 место", "minScore": "9", "maxScore": "10", "sortOrder": 0},
                    {"code": "SECOND", "label": "2 место", "minScore": "8", "maxScore": "8.99", "sortOrder": 1},
                ],
            )
        )
        return self

    def seat(self, *, name: str = "Иванова А.", email: str = "a@b.ru", genres: list[uuid.UUID] | None = None) -> tuple[str, uuid.UUID]:
        """Seat a judge, accept their invitation, and hand back their account."""
        member = self.config.invite(
            InviteJuryMemberCommand(
                competition_id=str(COMPETITION),
                full_name=name,
                email=email,
                category_ids=[str(item) for item in (genres or [])],
            )
        )
        user_id = uuid.uuid4()
        self.config.accept_invitation(token=self.tokens.issued[-1], user_id=str(user_id))
        return member.id, user_id

    def criterion_id(self, *, category_id: uuid.UUID = VOCALS) -> str:
        setup = self.config.setup(str(COMPETITION))
        sheet = next(item for item in setup.criteria_sets if item.target_id == str(category_id))
        return sheet.criteria[0].id


class TestTheJudgingModeGuard:
    def test_a_protocol_festival_cannot_be_scored(self) -> None:
        """The rule that stops a tablet left open from last season writing marks into a
        festival whose organizer has since switched back to protocols."""
        festival = Festival(online=False)

        with pytest.raises(OnlineJudgingDisabledError):
            festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))

    def test_the_setup_screen_still_opens_on_a_protocol_festival(self) -> None:
        """The award scale is used under both modes, so the screen is not gated."""
        festival = Festival(online=False)

        view = festival.config.setup(str(COMPETITION))

        assert view.online_judging is False
        assert len(view.award_scale) == 9, "the platform's defaults are offered"


class TestInvitations:
    def test_inviting_seats_somebody_and_writes_to_them(self) -> None:
        festival = Festival()

        member = festival.config.invite(InviteJuryMemberCommand(competition_id=str(COMPETITION), full_name="Иванова А.", email="A@B.ru"))

        assert member.status == "INVITED"
        assert member.has_account is False
        assert festival.notifier.sent[0]["email"] == "a@b.ru"

    def test_accepting_attaches_the_account_and_burns_the_link(self) -> None:
        festival = Festival()
        festival.config.invite(InviteJuryMemberCommand(competition_id=str(COMPETITION), full_name="И.", email="a@b.ru"))
        token = festival.tokens.issued[-1]

        member = festival.config.accept_invitation(token=token, user_id=str(uuid.uuid4()))

        assert member.status == "ACTIVE"
        assert member.invitation_path is None
        assert festival.members.by_invitation_token(token) is None

    def test_an_unknown_link_seats_nobody(self) -> None:
        festival = Festival()

        with pytest.raises(JuryMemberNotFoundError):
            festival.config.accept_invitation(token="nonsense", user_id=str(uuid.uuid4()))


class TestScoring:
    def test_a_judge_sends_a_sheet_for_an_open_act(self) -> None:
        festival = Festival().with_criteria()
        _, user_id = festival.seat()
        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))

        task = festival.scoring.submit_scorecard(
            SubmitScorecardCommand(
                competition_id=str(COMPETITION),
                submission_id=str(ACT_ONE),
                user_id=str(user_id),
                scores={festival.criterion_id(): Decimal("9.5")},
                comment="чисто",
            )
        )

        assert task.my_total == Decimal("9.50")
        assert task.my_comment == "чисто"

    def test_a_closed_act_refuses_a_sheet(self) -> None:
        festival = Festival().with_criteria()
        _, user_id = festival.seat()
        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))
        festival.scoring.close_scoring(CloseScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))

        with pytest.raises(PerformanceClosedError):
            festival.scoring.submit_scorecard(
                SubmitScorecardCommand(
                    competition_id=str(COMPETITION),
                    submission_id=str(ACT_ONE),
                    user_id=str(user_id),
                    scores={festival.criterion_id(): Decimal("9.5")},
                )
            )

    def test_an_act_the_host_never_opened_refuses_a_sheet(self) -> None:
        festival = Festival().with_criteria()
        _, user_id = festival.seat()

        with pytest.raises(ScoringNotFoundError):
            festival.scoring.submit_scorecard(
                SubmitScorecardCommand(
                    competition_id=str(COMPETITION),
                    submission_id=str(ACT_ONE),
                    user_id=str(user_id),
                    scores={festival.criterion_id(): Decimal("9.5")},
                )
            )

    def test_a_judge_seated_elsewhere_cannot_score_this_genre(self) -> None:
        """ARCH-001 §12.3, narrowed to the genre because that is how a panel is seated."""
        festival = Festival().with_criteria()
        _, user_id = festival.seat(genres=[DANCE])
        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))

        with pytest.raises(NotAssignedToGenreError):
            festival.scoring.submit_scorecard(
                SubmitScorecardCommand(
                    competition_id=str(COMPETITION),
                    submission_id=str(ACT_ONE),
                    user_id=str(user_id),
                    scores={festival.criterion_id(): Decimal("9.5")},
                )
            )

    def test_somebody_who_is_not_on_the_panel_cannot_score(self) -> None:
        festival = Festival().with_criteria()
        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))

        with pytest.raises(JuryMemberNotFoundError):
            festival.scoring.submit_scorecard(
                SubmitScorecardCommand(
                    competition_id=str(COMPETITION),
                    submission_id=str(ACT_ONE),
                    user_id=str(uuid.uuid4()),
                    scores={festival.criterion_id(): Decimal("9.5")},
                )
            )

    def test_opening_the_next_act_closes_the_one_before(self) -> None:
        """What a host pressing "следующий номер" means."""
        festival = Festival().with_criteria().with_criteria(category_id=DANCE)
        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))

        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_TWO)))

        states = {item.submission_id: item.status for item in festival.scoring.states(str(COMPETITION))}
        assert states[str(ACT_ONE)] == "CLOSED"
        assert states[str(ACT_TWO)] == "OPEN"

    def test_a_judge_can_go_back_to_a_number_they_missed(self) -> None:
        """The organizer's rule: the host drives the programme, the judge may still
        return to an act they skipped — as long as it is open."""
        festival = Festival().with_criteria().with_criteria(category_id=DANCE)
        _, user_id = festival.seat()

        tasks = festival.scoring.tasks_for_judge(competition_id=str(COMPETITION), user_id=str(user_id))

        assert {item.submission_id for item in tasks} == {str(ACT_ONE), str(ACT_TWO)}

    def test_a_judges_tablet_never_shows_a_participant(self) -> None:
        """ADR-0013, kept at the boundary: the projection has no name to leak."""
        festival = Festival().with_criteria()
        _, user_id = festival.seat(genres=[VOCALS])

        task = next(item for item in festival.scoring.tasks_for_judge(competition_id=str(COMPETITION), user_id=str(user_id)))

        assert task.title == "Журавли"
        assert task.organization == "ДШИ №3"
        assert not hasattr(task, "participants")


class TestTally:
    def _scored_festival(self, mark: str = "9.5") -> Festival:
        festival = Festival().with_criteria().with_places()
        _, user_id = festival.seat(genres=[VOCALS])
        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))
        festival.scoring.submit_scorecard(
            SubmitScorecardCommand(
                competition_id=str(COMPETITION),
                submission_id=str(ACT_ONE),
                user_id=str(user_id),
                scores={festival.criterion_id(): Decimal(mark)},
            )
        )
        return festival

    def test_the_tally_names_the_award_the_band_earned(self) -> None:
        festival = self._scored_festival()

        sheet = festival.scoring.tally(str(COMPETITION))
        vocals = next(group for group in sheet.groups if group.category_id == str(VOCALS))
        act = next(item for item in vocals.tallies if item.submission_id == str(ACT_ONE))

        assert act.score == Decimal("9.50")
        assert act.award_label == "1 место"

    def test_an_act_outside_every_band_is_counted_as_a_warning(self) -> None:
        festival = self._scored_festival(mark="5")

        sheet = festival.scoring.tally(str(COMPETITION))

        assert sheet.unawarded_count == 1

    def test_the_organizer_sees_each_judges_own_mark_and_comment(self) -> None:
        festival = self._scored_festival()

        sheet = festival.scoring.tally(str(COMPETITION))
        act = next(item for group in sheet.groups for item in group.tallies if item.submission_id == str(ACT_ONE))

        assert act.scorecards[0].jury_member_name == "Иванова А."
        assert act.scorecards[0].total == Decimal("9.50")

    def test_a_judge_seated_elsewhere_is_not_expected_on_this_act(self) -> None:
        """Otherwise every вокал act reads "1 из 2" for the whole festival."""
        festival = self._scored_festival()
        festival.seat(name="Петров Б.", email="b@c.ru", genres=[DANCE])

        sheet = festival.scoring.tally(str(COMPETITION))
        act = next(item for group in sheet.groups for item in group.tallies if item.submission_id == str(ACT_ONE))

        assert act.expected_judges == 1


class TestApplyingToProtocols:
    def test_the_computed_awards_are_pushed_one_genre_at_a_time(self) -> None:
        festival = Festival().with_criteria().with_places()
        _, user_id = festival.seat(genres=[VOCALS])
        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))
        festival.scoring.submit_scorecard(
            SubmitScorecardCommand(
                competition_id=str(COMPETITION),
                submission_id=str(ACT_ONE),
                user_id=str(user_id),
                scores={festival.criterion_id(): Decimal("9.5")},
            )
        )

        changed = festival.scoring.apply_to_protocols(str(COMPETITION))

        assert changed == 1
        _, nomination_id, awards = festival.protocols.calls[0]
        assert nomination_id == VOCALS
        assert awards == [(ACT_ONE, "FIRST")]

    def test_an_unjudged_act_is_left_alone(self) -> None:
        """An organizer may have typed that result in by hand, and a tally push that
        blanked it would overrule them."""
        festival = Festival().with_criteria().with_places()

        changed = festival.scoring.apply_to_protocols(str(COMPETITION))

        assert changed == 0
        assert festival.protocols.calls == []


class TestTheHallBoard:
    def _board_festival(self, *, reveal: str, visibility: str) -> Festival:
        festival = Festival().with_criteria().with_places()
        festival.config.update_board(
            UpdateBoardCommand(
                competition_id=str(COMPETITION),
                enabled=True,
                visibility=visibility,
                reveal=reveal,
            )
        )
        _, user_id = festival.seat(genres=[VOCALS])
        festival.scoring.open_scoring(OpenScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))
        festival.scoring.submit_scorecard(
            SubmitScorecardCommand(
                competition_id=str(COMPETITION),
                submission_id=str(ACT_ONE),
                user_id=str(user_id),
                scores={festival.criterion_id(): Decimal("9.5")},
            )
        )
        return festival

    def test_a_board_that_reveals_immediately_shows_the_mark_at_once(self) -> None:
        festival = self._board_festival(reveal="IMMEDIATE", visibility="PER_JUDGE")

        board = festival.scoring.board("BoardSlug1")

        assert board is not None
        assert board.current is not None
        assert board.current.score == Decimal("9.50")
        assert board.current.judges[0].name == "Иванова А."

    def test_a_board_that_waits_shows_nothing_until_the_host_closes_the_act(self) -> None:
        festival = self._board_festival(reveal="AFTER_CLOSE", visibility="PER_JUDGE")

        board = festival.scoring.board("BoardSlug1")

        assert board is not None
        assert board.current is not None
        assert board.current.score is None
        assert board.current.submitted_count == 1, "the hall still sees that a sheet is in"

    def test_closing_the_act_reveals_it(self) -> None:
        festival = self._board_festival(reveal="AFTER_CLOSE", visibility="TOTAL_ONLY")
        festival.scoring.close_scoring(CloseScoringCommand(competition_id=str(COMPETITION), submission_id=str(ACT_ONE)))

        board = festival.scoring.board("BoardSlug1")

        assert board is not None
        entry = board.recent[0]
        assert entry.score == Decimal("9.50")
        assert entry.award_label == "1 место"

    def test_a_totals_only_board_never_carries_a_judges_name(self) -> None:
        """The filtering is in the service, so there is no query parameter that could
        turn it back on."""
        festival = self._board_festival(reveal="IMMEDIATE", visibility="TOTAL_ONLY")

        board = festival.scoring.board("BoardSlug1")

        assert board is not None
        assert board.current is not None
        assert board.current.judges == ()

    def test_a_board_that_was_switched_off_stops_resolving(self) -> None:
        festival = self._board_festival(reveal="IMMEDIATE", visibility="TOTAL_ONLY")
        festival.config.update_board(UpdateBoardCommand(competition_id=str(COMPETITION), enabled=False, visibility="TOTAL_ONLY", reveal="IMMEDIATE"))

        assert festival.scoring.board("BoardSlug1") is None

    def test_an_unknown_slug_is_no_board(self) -> None:
        assert Festival().scoring.board("nope") is None
