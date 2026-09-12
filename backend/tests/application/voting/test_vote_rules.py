"""The rules that decide whether a vote is counted.

Driven through the real service and the real repositories, but with the clock and
the voter identity injected, because the two things worth testing here — a ballot
that lets people back tomorrow, and a ceiling on one network — are about time and
about who you are, and neither is reachable through an HTTP client.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from apps.voting.application.commands import AddNomineeCommand, CastVoteCommand, CreateBallotCommand, NomineeRow
from apps.voting.application.interfaces import VoterTokens
from apps.voting.application.services import BallotService
from apps.voting.domain.exceptions import AlreadyVotedError, TooManyVotesFromNetworkError, VoteLimitReachedError
from apps.voting.domain.vote import NetworkKey, VoterKey
from apps.voting.infrastructure.repositories import DjangoBallotRepository, DjangoVoteRepository
from apps.voting.infrastructure.system import RandomSlugFactory, Uuid7Generator

pytestmark = pytest.mark.django_db

START = datetime(2026, 9, 12, 18, 0, tzinfo=UTC)


class FrozenClock:
    """A clock the test moves by hand."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def utcnow(self) -> datetime:
        return self.now


def tokens(voter: str, network: str = "hall") -> VoterTokens:
    """One person, on one network. Opaque strings, as the domain sees them."""
    return VoterTokens(voter=VoterKey(f"voter-{voter}"), network=NetworkKey(f"net-{network}"))


def service(clock: FrozenClock) -> BallotService:
    return BallotService(
        ballots=DjangoBallotRepository(),
        votes=DjangoVoteRepository(),
        clock=clock,
        uuids=Uuid7Generator(),
        slugs=RandomSlugFactory(),
    )


def a_ballot(svc: BallotService, **settings: object) -> tuple[str, str, list[str]]:
    """An open ballot with three nominees; returns its id, its slug and their ids."""
    detail = svc.create(
        CreateBallotCommand(
            organization_id=str(uuid.uuid4()),
            title="Приз зрительских симпатий",
            **settings,  # type: ignore[arg-type]
        )
    )
    for name in ("Первый", "Второй", "Третий"):
        detail = svc.add_nominee(AddNomineeCommand(ballot_id=detail.id, nominee=NomineeRow(title=name)))
    opened = svc.open(uuid.UUID(detail.id))
    return opened.id, opened.slug, [row.id for row in opened.nominees]


class TestComingBackTomorrow:
    def test_a_one_shot_ballot_lets_nobody_vote_twice_however_long_they_wait(self) -> None:
        clock = FrozenClock(START)
        svc = service(clock)
        _, slug, nominees = a_ballot(svc)
        svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))

        clock.now = START + timedelta(days=30)

        with pytest.raises((AlreadyVotedError, VoteLimitReachedError)):
            svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))

    def test_a_daily_ballot_replenishes_the_next_day(self) -> None:
        """Some festivals run an online vote across a whole week on purpose."""
        clock = FrozenClock(START)
        svc = service(clock)
        _, slug, nominees = a_ballot(svc, cooldown_hours=24)
        svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))

        clock.now = START + timedelta(days=1)
        receipt = svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))

        assert receipt.accepted == (nominees[0],)

    def test_the_same_day_is_still_one_window(self) -> None:
        clock = FrozenClock(START)
        svc = service(clock)
        _, slug, nominees = a_ballot(svc, cooldown_hours=24)
        svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))

        clock.now = START + timedelta(hours=3)

        with pytest.raises((AlreadyVotedError, VoteLimitReachedError)):
            svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))

    def test_both_days_are_counted(self) -> None:
        clock = FrozenClock(START)
        svc = service(clock)
        ballot_id, slug, nominees = a_ballot(svc, cooldown_hours=24)
        svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))
        clock.now = START + timedelta(days=1)
        svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))

        detail = svc.get(uuid.UUID(ballot_id))

        assert detail.total_votes == 2
        # Two votes, one person: the turnout and the vote count are different numbers,
        # and an organizer reading only one of them draws the wrong conclusion about
        # how many people came.
        assert detail.voters == 1


class TestTheNetworkBrake:
    def test_one_network_is_stopped_once_it_sends_implausibly_many(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A script from one machine. The ceiling is high; this test lowers it."""
        monkeypatch.setattr("apps.voting.application.services.NETWORK_VOTE_CEILING", 2)
        clock = FrozenClock(START)
        svc = service(clock)
        _, slug, nominees = a_ballot(svc)

        for index in range(2):
            svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens(f"person-{index}"))

        with pytest.raises(TooManyVotesFromNetworkError):
            svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("person-3"))

    def test_another_network_is_unaffected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A hall shares one address between hundreds of phones; a ceiling is per network."""
        monkeypatch.setattr("apps.voting.application.services.NETWORK_VOTE_CEILING", 2)
        clock = FrozenClock(START)
        svc = service(clock)
        _, slug, nominees = a_ballot(svc)
        for index in range(2):
            svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens(f"person-{index}"))

        receipt = svc.cast_vote(
            CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)),
            tokens=tokens("elsewhere", network="mobile"),
        )

        assert receipt.accepted == (nominees[0],)

    def test_the_brake_lifts_in_the_next_window(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("apps.voting.application.services.NETWORK_VOTE_CEILING", 1)
        clock = FrozenClock(START)
        svc = service(clock)
        _, slug, nominees = a_ballot(svc, cooldown_hours=24)
        svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("anna"))

        clock.now = START + timedelta(days=1)
        receipt = svc.cast_vote(CastVoteCommand(slug=slug, nominee_ids=(nominees[0],)), tokens=tokens("boris"))

        assert receipt.accepted == (nominees[0],)


class TestBatchEditsSurviveTheVersionGuard:
    def test_many_nominees_can_be_added_before_one_save(self) -> None:
        """A fifty-row import bumps the version fifty times and must still persist."""
        clock = FrozenClock(START)
        svc = service(clock)
        detail = svc.create(CreateBallotCommand(organization_id=str(uuid.uuid4()), title="Большой список"))

        from apps.voting.application.commands import ImportNomineesCommand

        preview = svc.import_nominees(
            ImportNomineesCommand(
                ballot_id=detail.id,
                rows=tuple(NomineeRow(title=f"Участник {index}") for index in range(50)),
            )
        )

        assert len(preview.added) == 50
        assert len(svc.get(uuid.UUID(detail.id)).nominees) == 50
