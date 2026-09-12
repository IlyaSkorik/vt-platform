"""Unit tests for the Voting value objects."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.voting.domain.exceptions import InvalidBallotDataError
from apps.voting.domain.value_objects import (
    COOLDOWN_MAX_HOURS,
    VOTES_PER_VOTER_MAX,
    BallotTitle,
    Cooldown,
    NomineeText,
    PublicSlug,
    VoteLimit,
    VotingWindow,
)

NOW = datetime(2026, 9, 12, 18, 0, tzinfo=UTC)


class TestBallotTitle:
    def test_it_collapses_the_whitespace_somebody_pasted_in(self) -> None:
        assert BallotTitle("  Приз   зрительских  симпатий ").value == "Приз зрительских симпатий"

    def test_a_blank_title_is_refused(self) -> None:
        with pytest.raises(InvalidBallotDataError):
            BallotTitle("   ")

    def test_an_overlong_title_is_refused(self) -> None:
        with pytest.raises(InvalidBallotDataError):
            BallotTitle("я" * 201)


class TestNomineeText:
    def test_blank_is_allowed_because_a_city_is_optional(self) -> None:
        assert NomineeText("").empty is True

    def test_an_overlong_line_is_refused(self) -> None:
        with pytest.raises(InvalidBallotDataError):
            NomineeText("я" * 201)


class TestPublicSlug:
    def test_a_generated_slug_avoids_confusable_characters(self) -> None:
        """These links get typed off posters and read aloud from stages."""
        for _ in range(200):
            assert not set(PublicSlug.generate().value) & set("0O1lI")

    def test_a_slug_with_a_forbidden_character_is_refused(self) -> None:
        with pytest.raises(InvalidBallotDataError):
            PublicSlug("abc-def")

    def test_a_slug_too_short_to_be_unguessable_is_refused(self) -> None:
        with pytest.raises(InvalidBallotDataError):
            PublicSlug("abc")

    def test_generated_slugs_do_not_repeat(self) -> None:
        assert len({PublicSlug.generate().value for _ in range(500)}) == 500


class TestVotingWindow:
    def test_an_unbounded_window_contains_everything(self) -> None:
        assert VotingWindow().contains(NOW) is True

    def test_it_excludes_a_moment_before_it_opens(self) -> None:
        assert VotingWindow(opens_at=NOW + timedelta(hours=1)).contains(NOW) is False

    def test_the_closing_instant_is_already_outside(self) -> None:
        window = VotingWindow(closes_at=NOW)

        assert window.contains(NOW) is False
        assert window.contains(NOW - timedelta(seconds=1)) is True

    def test_a_window_that_closes_before_it_opens_is_refused(self) -> None:
        with pytest.raises(InvalidBallotDataError):
            VotingWindow(opens_at=NOW, closes_at=NOW - timedelta(hours=1))

    def test_expiry_is_about_the_far_end_only(self) -> None:
        assert VotingWindow(closes_at=NOW).has_expired(NOW) is True
        assert VotingWindow().has_expired(NOW) is False


class TestVoteLimit:
    def test_one_vote_is_the_default(self) -> None:
        assert VoteLimit().value == 1

    @pytest.mark.parametrize("bad", [0, -1, VOTES_PER_VOTER_MAX + 1])
    def test_an_implausible_limit_is_refused(self, bad: int) -> None:
        with pytest.raises(InvalidBallotDataError):
            VoteLimit(bad)

    def test_a_boolean_is_not_a_number_of_votes(self) -> None:
        with pytest.raises(InvalidBallotDataError):
            VoteLimit(True)  # type: ignore[arg-type]


class TestCooldown:
    def test_zero_means_once_for_the_whole_ballot(self) -> None:
        cooldown = Cooldown(0)

        assert cooldown.repeating is False
        assert cooldown.bucket(NOW) == 0
        assert cooldown.bucket(NOW + timedelta(days=30)) == 0

    def test_a_daily_ballot_puts_two_days_in_different_windows(self) -> None:
        cooldown = Cooldown(24)

        assert cooldown.bucket(NOW) != cooldown.bucket(NOW + timedelta(days=1))

    def test_the_same_day_is_one_window(self) -> None:
        cooldown = Cooldown(24)

        assert cooldown.bucket(NOW) == cooldown.bucket(NOW + timedelta(minutes=30))

    @pytest.mark.parametrize("bad", [-1, COOLDOWN_MAX_HOURS + 1])
    def test_an_implausible_cooldown_is_refused(self, bad: int) -> None:
        with pytest.raises(InvalidBallotDataError):
            Cooldown(bad)
