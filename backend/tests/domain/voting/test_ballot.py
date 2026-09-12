"""Unit tests for the ``Ballot`` aggregate — framework-free."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from apps.voting.domain.entities import Ballot
from apps.voting.domain.exceptions import (
    BallotNotOpenError,
    InvalidBallotDataError,
    NomineeNotFoundError,
    NomineeWithdrawnError,
    TooFewNomineesError,
    VotingClosedError,
)
from apps.voting.domain.value_objects import (
    BallotStatus,
    BallotTitle,
    Cooldown,
    NomineeText,
    PublicSlug,
    RevealPolicy,
    VoteLimit,
    VotingWindow,
)

NOW = datetime(2026, 9, 12, 18, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=2)


def a_ballot(**overrides: object) -> Ballot:
    defaults: dict[str, object] = {
        "ballot_id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "title": BallotTitle("Приз зрительских симпатий"),
        "slug": PublicSlug.generate(),
        "now": NOW,
    }
    defaults.update(overrides)
    return Ballot.draft(**defaults)  # type: ignore[arg-type]


def with_nominees(ballot: Ballot, count: int = 2) -> Ballot:
    for index in range(count):
        ballot.add_nominee(
            nominee_id=uuid.uuid4(),
            title=NomineeText(f"Участник {index + 1}"),
            number=index + 1,
            now=NOW,
        )
    return ballot


def an_open_ballot(**overrides: object) -> Ballot:
    ballot = with_nominees(a_ballot(**overrides))
    ballot.open(now=NOW)
    return ballot


class TestStandingOnItsOwn:
    def test_a_ballot_needs_no_festival(self) -> None:
        """The whole reason this context exists: an audience vote without a competition."""
        ballot = a_ballot()

        assert ballot.competition_id is None
        assert ballot.standalone is True

    def test_a_ballot_may_still_name_a_festival(self) -> None:
        competition_id = uuid.uuid4()

        ballot = a_ballot(competition_id=competition_id)

        assert ballot.competition_id == competition_id
        assert ballot.standalone is False

    def test_a_nominee_carries_its_own_card_rather_than_a_reference(self) -> None:
        """A finished vote must stay readable after the programme it came from is gone."""
        ballot = a_ballot()

        nominee = ballot.add_nominee(
            nominee_id=uuid.uuid4(),
            title=NomineeText("Ансамбль «Ритм»"),
            subtitle=NomineeText("«Калинка»"),
            number=7,
            now=NOW,
        )

        assert nominee.title.value == "Ансамбль «Ритм»"
        assert nominee.subtitle.value == "«Калинка»"
        assert nominee.submission_id is None


class TestAssemblingTheList:
    def test_nominees_are_numbered_in_order(self) -> None:
        ballot = with_nominees(a_ballot(), count=3)

        assert [nominee.position for nominee in ballot.nominees] == [1, 2, 3]

    def test_reordering_rewrites_the_positions(self) -> None:
        ballot = with_nominees(a_ballot(), count=3)
        reversed_ids = [nominee.id for nominee in reversed(ballot.nominees)]

        ballot.reorder_nominees(reversed_ids, now=LATER)

        assert [nominee.id for nominee in ballot.nominees] == reversed_ids
        assert [nominee.position for nominee in ballot.nominees] == [1, 2, 3]

    def test_a_reorder_that_loses_somebody_is_refused(self) -> None:
        ballot = with_nominees(a_ballot(), count=3)

        with pytest.raises(InvalidBallotDataError):
            ballot.reorder_nominees([ballot.nominees[0].id], now=LATER)

    def test_a_nominee_nobody_voted_for_is_simply_removed(self) -> None:
        ballot = with_nominees(a_ballot(), count=3)
        doomed = ballot.nominees[1].id

        ballot.remove_nominee(doomed, now=LATER)

        assert doomed not in {nominee.id for nominee in ballot.nominees}

    def test_a_nominee_with_votes_is_withdrawn_rather_than_erased(self) -> None:
        """Deleting the row would quietly change a total people have already seen."""
        ballot = an_open_ballot()
        voted_for = ballot.nominees[0].id
        ballot.accept_vote_for(voted_for, now=NOW)

        ballot.remove_nominee(voted_for, now=LATER)

        nominee = ballot.nominee(voted_for)
        assert nominee.withdrawn is True
        assert nominee.votes == 1
        assert voted_for not in {candidate.id for candidate in ballot.votable}

    def test_a_nominee_can_be_added_after_the_vote_opened(self) -> None:
        """An act added to the running order on the day has to be votable on the day."""
        ballot = an_open_ballot()

        ballot.add_nominee(nominee_id=uuid.uuid4(), title=NomineeText("Опоздавший"), now=LATER)

        assert len(ballot.votable) == 3

    def test_asking_for_a_nominee_that_is_not_here_is_an_error(self) -> None:
        with pytest.raises(NomineeNotFoundError):
            a_ballot().nominee(uuid.uuid4())


class TestOpeningAndClosing:
    def test_a_ballot_opens_once_it_has_something_to_choose_between(self) -> None:
        ballot = with_nominees(a_ballot())

        ballot.open(now=NOW)

        assert ballot.status is BallotStatus.OPEN
        assert ballot.opened_at == NOW

    def test_a_vote_with_one_option_is_not_a_vote(self) -> None:
        ballot = with_nominees(a_ballot(), count=1)

        with pytest.raises(TooFewNomineesError):
            ballot.open(now=NOW)

    def test_withdrawn_nominees_do_not_count_towards_the_minimum(self) -> None:
        ballot = with_nominees(a_ballot(), count=2)
        ballot.nominees[0].withdraw()

        with pytest.raises(TooFewNomineesError):
            ballot.open(now=NOW)

    def test_opening_an_already_open_ballot_changes_nothing(self) -> None:
        ballot = an_open_ballot()
        opened = ballot.opened_at

        ballot.open(now=LATER)

        assert ballot.opened_at == opened

    def test_a_ballot_whose_window_has_passed_cannot_be_opened(self) -> None:
        ballot = with_nominees(a_ballot(window=VotingWindow(closes_at=NOW - timedelta(hours=1))))

        with pytest.raises(VotingClosedError):
            ballot.open(now=NOW)

    def test_closing_is_one_way(self) -> None:
        """A ballot that could be reopened is a result that can be revised."""
        ballot = an_open_ballot()
        ballot.close(now=LATER)

        with pytest.raises(BallotNotOpenError):
            ballot.open(now=LATER)

    def test_a_closed_ballot_cannot_be_edited(self) -> None:
        ballot = an_open_ballot()
        ballot.close(now=LATER)

        with pytest.raises(BallotNotOpenError):
            ballot.update(title=BallotTitle("Другое название"), now=LATER)


class TestAcceptingVotes:
    def test_a_vote_advances_the_nominee(self) -> None:
        ballot = an_open_ballot()
        target = ballot.nominees[0].id

        ballot.accept_vote_for(target, now=NOW)

        assert ballot.nominee(target).votes == 1
        assert ballot.total_votes == 1

    def test_a_draft_ballot_takes_no_votes(self) -> None:
        ballot = with_nominees(a_ballot())

        with pytest.raises(VotingClosedError):
            ballot.accept_vote_for(ballot.nominees[0].id, now=NOW)

    def test_a_vote_before_the_window_opens_is_refused(self) -> None:
        ballot = an_open_ballot(window=VotingWindow(opens_at=NOW + timedelta(hours=1)))

        with pytest.raises(VotingClosedError):
            ballot.accept_vote_for(ballot.nominees[0].id, now=NOW)

    def test_a_vote_after_the_window_closes_is_refused_without_anyone_flipping_a_switch(self) -> None:
        """The state must not depend on a cron having fired."""
        ballot = an_open_ballot(window=VotingWindow(closes_at=NOW + timedelta(hours=1)))

        with pytest.raises(VotingClosedError):
            ballot.accept_vote_for(ballot.nominees[0].id, now=NOW + timedelta(hours=2))

    def test_a_withdrawn_nominee_takes_no_votes(self) -> None:
        ballot = an_open_ballot()
        target = ballot.nominees[0]
        target.withdraw()

        with pytest.raises(NomineeWithdrawnError):
            ballot.accept_vote_for(target.id, now=NOW)


class TestShowingTheCount:
    def test_after_close_hides_the_running_total_by_default(self) -> None:
        """A live scoreboard tells a stuffer exactly how many votes they still need."""
        ballot = an_open_ballot()

        assert ballot.reveal is RevealPolicy.AFTER_CLOSE
        assert ballot.may_reveal_totals(now=NOW) is False

    def test_after_close_shows_it_once_the_vote_is_over(self) -> None:
        ballot = an_open_ballot()
        ballot.close(now=LATER)

        assert ballot.may_reveal_totals(now=LATER) is True

    def test_always_shows_it_while_voting(self) -> None:
        ballot = an_open_ballot(reveal=RevealPolicy.ALWAYS)

        assert ballot.may_reveal_totals(now=NOW) is True

    def test_never_keeps_it_from_the_public_even_afterwards(self) -> None:
        ballot = an_open_ballot(reveal=RevealPolicy.NEVER)
        ballot.close(now=LATER)

        assert ballot.may_reveal_totals(now=LATER) is False

    def test_a_draft_reveals_nothing(self) -> None:
        assert with_nominees(a_ballot()).may_reveal_totals(now=NOW) is False


class TestSettings:
    def test_the_rules_can_be_changed_while_the_vote_runs(self) -> None:
        ballot = an_open_ballot()

        ballot.update(window=VotingWindow(closes_at=NOW + timedelta(hours=4)), now=LATER)

        assert ballot.window.closes_at == NOW + timedelta(hours=4)

    def test_the_vote_limit_and_cooldown_are_carried_on_the_ballot(self) -> None:
        ballot = a_ballot(vote_limit=VoteLimit(3), cooldown=Cooldown(24))

        assert ballot.vote_limit.value == 3
        assert ballot.cooldown.hours == 24
