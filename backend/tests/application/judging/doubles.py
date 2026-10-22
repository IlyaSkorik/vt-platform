"""In-memory doubles for the Judging ports.

The use cases are written against protocols, so a whole festival day — a host opening
acts, five judges sending sheets, a board being read in the hall — can be exercised
without PostgreSQL, without the Applications context and without a real clock.

:class:`RecordingProtocolWriter` and :class:`RecordingNotifier` are the two that matter
for assertions: pushing a tally into protocols and inviting a judge are effects, and
recording the calls is how a test says what should have happened without a protocol
aggregate or an SMTP server anywhere in sight.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.judging.application.interfaces import DirectoryCompetition, DirectoryNomination, DirectoryPerformance, ProtocolApplication
from apps.judging.domain.entities import JudgingSetup, JuryMember, PerformanceScoring, Scorecard
from apps.judging.domain.value_objects import JuryMemberStatus, PerformanceScoringStatus

__all__ = [
    "FixedClock",
    "InMemoryJudgingSetupRepository",
    "InMemoryJuryMemberRepository",
    "InMemoryPerformanceScoringRepository",
    "InMemoryScorecardRepository",
    "RecordingNotifier",
    "RecordingProtocolWriter",
    "ScriptedSlugFactory",
    "ScriptedTokenFactory",
    "SequentialUuids",
    "StubCompetitionDirectory",
    "StubPerformanceDirectory",
]


class FixedClock:
    """A clock that never moves, so every timestamp in a test is predictable."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 5, 16, 11, 0, tzinfo=UTC)

    def utcnow(self) -> datetime:
        return self._now


class SequentialUuids:
    """Fresh ids, real ones — nothing here depends on them being ordered."""

    def new(self) -> uuid.UUID:
        return uuid.uuid4()


class ScriptedSlugFactory:
    def __init__(self, slug: str = "BoardSlug1") -> None:
        self._slug = slug

    def new_slug(self) -> str:
        return self._slug


class ScriptedTokenFactory:
    """Predictable invitation tokens, so a test can follow the link it just issued."""

    def __init__(self) -> None:
        self.issued: list[str] = []

    def new_token(self) -> str:
        token = f"token-{len(self.issued) + 1}"
        self.issued.append(token)
        return token


class InMemoryJudgingSetupRepository:
    def __init__(self) -> None:
        self._by_competition: dict[uuid.UUID, JudgingSetup] = {}

    def get(self, competition_id: uuid.UUID) -> JudgingSetup | None:
        return self._by_competition.get(competition_id)

    def by_board_slug(self, slug: str) -> JudgingSetup | None:
        for setup in self._by_competition.values():
            if setup.board_slug == slug and setup.board.enabled:
                return setup
        return None

    def save(self, setup: JudgingSetup) -> None:
        self._by_competition[setup.competition_id] = setup


class InMemoryJuryMemberRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, JuryMember] = {}

    def get(self, member_id: uuid.UUID) -> JuryMember | None:
        return self._by_id.get(member_id)

    def by_competition(self, competition_id: uuid.UUID) -> tuple[JuryMember, ...]:
        members = [item for item in self._by_id.values() if item.competition_id == competition_id]
        return tuple(sorted(members, key=lambda item: (item.sort_order, item.full_name)))

    def by_user(self, *, competition_id: uuid.UUID, user_id: uuid.UUID) -> JuryMember | None:
        return next(
            (item for item in self._by_id.values() if item.competition_id == competition_id and item.user_id == user_id),
            None,
        )

    def by_invitation_token(self, token: str) -> JuryMember | None:
        return next((item for item in self._by_id.values() if item.invitation_token == token), None)

    def competitions_for_user(self, user_id: uuid.UUID) -> tuple[JuryMember, ...]:
        return tuple(item for item in self._by_id.values() if item.user_id == user_id and item.status is JuryMemberStatus.ACTIVE)

    def save(self, member: JuryMember) -> None:
        self._by_id[member.id] = member

    def delete(self, member_id: uuid.UUID) -> None:
        self._by_id.pop(member_id, None)


class InMemoryPerformanceScoringRepository:
    def __init__(self) -> None:
        self._by_key: dict[tuple[uuid.UUID, uuid.UUID], PerformanceScoring] = {}

    def get(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID) -> PerformanceScoring | None:
        return self._by_key.get((competition_id, submission_id))

    def by_competition(self, competition_id: uuid.UUID) -> tuple[PerformanceScoring, ...]:
        return tuple(item for (comp, _), item in self._by_key.items() if comp == competition_id)

    def current(self, competition_id: uuid.UUID) -> PerformanceScoring | None:
        open_ones = [item for item in self.by_competition(competition_id) if item.status is PerformanceScoringStatus.OPEN]
        return max(open_ones, key=lambda item: item.opened_at or item.updated_at) if open_ones else None

    def save(self, scoring: PerformanceScoring) -> None:
        self._by_key[(scoring.competition_id, scoring.submission_id)] = scoring


class InMemoryScorecardRepository:
    def __init__(self) -> None:
        self._by_key: dict[tuple[uuid.UUID, uuid.UUID], Scorecard] = {}

    def get(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID, jury_member_id: uuid.UUID) -> Scorecard | None:
        card = self._by_key.get((submission_id, jury_member_id))
        return card if card is not None and card.competition_id == competition_id else None

    def by_submission(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID) -> tuple[Scorecard, ...]:
        return tuple(item for item in self._by_key.values() if item.competition_id == competition_id and item.submission_id == submission_id)

    def by_submissions(self, *, competition_id: uuid.UUID, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[Scorecard, ...]]:
        wanted = set(submission_ids)
        grouped: dict[uuid.UUID, list[Scorecard]] = {}
        for card in self._by_key.values():
            if card.competition_id == competition_id and card.submission_id in wanted:
                grouped.setdefault(card.submission_id, []).append(card)
        return {key: tuple(value) for key, value in grouped.items()}

    def by_member(self, *, competition_id: uuid.UUID, jury_member_id: uuid.UUID) -> tuple[Scorecard, ...]:
        return tuple(item for item in self._by_key.values() if item.competition_id == competition_id and item.jury_member_id == jury_member_id)

    def save(self, scorecard: Scorecard) -> None:
        self._by_key[(scorecard.submission_id, scorecard.jury_member_id)] = scorecard


class StubCompetitionDirectory:
    """A festival's taxonomy and its judging mode, both settable by the test."""

    def __init__(self, *, online: bool = True, nominations: Sequence[DirectoryNomination] = (), title: str = "Весна") -> None:
        self.online = online
        self._nominations = tuple(nominations)
        self._title = title

    def nominations(self, competition_id: uuid.UUID) -> tuple[DirectoryNomination, ...]:
        return self._nominations

    def competition_title(self, competition_id: uuid.UUID) -> str:
        return self._title

    def competitions(self, competition_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, DirectoryCompetition]:
        return {
            identifier: DirectoryCompetition(competition_id=identifier, title=self._title, online_judging=self.online)
            for identifier in competition_ids
        }

    def online_judging_enabled(self, competition_id: uuid.UUID) -> bool:
        return self.online

    def organizer_id(self, competition_id: uuid.UUID) -> uuid.UUID | None:
        return None


class StubPerformanceDirectory:
    def __init__(self, performances: Sequence[DirectoryPerformance] = ()) -> None:
        self._performances = tuple(performances)

    def performances(self, competition_id: uuid.UUID) -> tuple[DirectoryPerformance, ...]:
        return self._performances

    def performances_by_id(self, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, DirectoryPerformance]:
        wanted = set(submission_ids)
        return {item.submission_id: item for item in self._performances if item.submission_id in wanted}


class RecordingProtocolWriter:
    """Records what would have been written into Results, and how much of it landed.

    ``missing`` names the genres that have no protocol open, so a test can exercise the
    answer an organizer actually needs: not "nothing changed" but "there is nowhere to
    write this yet".
    """

    def __init__(self, *, rows_changed: int | None = None, missing: Sequence[uuid.UUID] = ()) -> None:
        self.calls: list[tuple[uuid.UUID, uuid.UUID, list[tuple[uuid.UUID, str | None]]]] = []
        self._rows_changed = rows_changed
        self._missing = set(missing)

    def apply_awards(
        self,
        *,
        competition_id: uuid.UUID,
        nomination_id: uuid.UUID,
        awards: Sequence[tuple[uuid.UUID, str | None]],
        now: datetime,
        create_missing: bool = False,
    ) -> ProtocolApplication:
        self.calls.append((competition_id, nomination_id, list(awards)))
        if nomination_id in self._missing:
            if not create_missing:
                return ProtocolApplication(rows_changed=0, protocol_existed=False)
            self._missing.discard(nomination_id)
            rows = self._rows_changed if self._rows_changed is not None else len(awards)
            return ProtocolApplication(rows_changed=rows, protocol_existed=True, protocol_created=True)
        rows = self._rows_changed if self._rows_changed is not None else len(awards)
        return ProtocolApplication(rows_changed=rows, protocol_existed=True)


class RecordingNotifier:
    """Records the invitations that would have gone out."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def notify_jury_invited(self, *, email: str, full_name: str, competition_title: str, invitation_url: str) -> bool:
        self.sent.append({"email": email, "full_name": full_name, "competition_title": competition_title, "invitation_url": invitation_url})
        return True
