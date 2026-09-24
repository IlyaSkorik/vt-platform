"""Django adapters for the Judging repositories.

Four small stores, one per aggregate. Each is a straight ``update_or_create`` over one
table — none of these aggregates owns child rows, which is what the JSON columns in
:mod:`apps.judging.infrastructure.models` bought.

Everything filters on ``deleted_at__isnull=True``: a revoked jury member is soft-deleted
only when the organizer removes them outright, and a removed seat must stop appearing
on the panel while the marks it gave stay where they are.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from django.utils import timezone

from apps.judging.domain.entities import JudgingSetup, JuryMember, PerformanceScoring, Scorecard
from apps.judging.domain.value_objects import PerformanceScoringStatus
from apps.judging.infrastructure.mappers.panel_mapper import (
    member_to_model,
    scorecard_to_model,
    scoring_to_model,
    to_member,
    to_scorecard,
    to_scoring,
)
from apps.judging.infrastructure.mappers.setup_mapper import setup_to_model, to_setup
from apps.judging.infrastructure.models import (
    JudgingSetupModel,
    JuryMemberModel,
    PerformanceScoringModel,
    ScorecardModel,
)

__all__ = [
    "DjangoJudgingSetupRepository",
    "DjangoJuryMemberRepository",
    "DjangoPerformanceScoringRepository",
    "DjangoScorecardRepository",
]


class DjangoJudgingSetupRepository:
    """Loads and stores the one configuration row a competition has."""

    def get(self, competition_id: uuid.UUID) -> JudgingSetup | None:
        model = JudgingSetupModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).first()
        return None if model is None else to_setup(model)

    def by_board_slug(self, slug: str) -> JudgingSetup | None:
        """Resolve the hall board's public link, or ``None``.

        Only answers while the board is switched on: turning it off has to take the
        screen down, and a slug that kept resolving would leave last season's marks on
        a URL somebody still has open.
        """
        if not slug:
            return None
        model = JudgingSetupModel.objects.filter(board_slug=slug, deleted_at__isnull=True).first()
        if model is None:
            return None
        setup = to_setup(model)
        return setup if setup.board.enabled else None

    def save(self, setup: JudgingSetup) -> None:
        JudgingSetupModel.objects.update_or_create(id=setup.id, defaults=setup_to_model(setup))


class DjangoJuryMemberRepository:
    """Loads and stores the panel."""

    def get(self, member_id: uuid.UUID) -> JuryMember | None:
        model = JuryMemberModel.objects.filter(id=member_id, deleted_at__isnull=True).first()
        return None if model is None else to_member(model)

    def by_competition(self, competition_id: uuid.UUID) -> tuple[JuryMember, ...]:
        rows = JuryMemberModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("sort_order", "full_name")
        return tuple(to_member(model) for model in rows)

    def by_user(self, *, competition_id: uuid.UUID, user_id: uuid.UUID) -> JuryMember | None:
        model = JuryMemberModel.objects.filter(competition_id=competition_id, user_id=user_id, deleted_at__isnull=True).first()
        return None if model is None else to_member(model)

    def by_invitation_token(self, token: str) -> JuryMember | None:
        if not token:
            return None
        model = JuryMemberModel.objects.filter(invitation_token=token, deleted_at__isnull=True).first()
        return None if model is None else to_member(model)

    def competitions_for_user(self, user_id: uuid.UUID) -> tuple[JuryMember, ...]:
        """Every seat this account holds — the judge's "мои фестивали" list."""
        rows = JuryMemberModel.objects.filter(user_id=user_id, status="ACTIVE", deleted_at__isnull=True).order_by("-created_at")
        return tuple(to_member(model) for model in rows)

    def save(self, member: JuryMember) -> None:
        JuryMemberModel.objects.update_or_create(id=member.id, defaults=member_to_model(member))

    def delete(self, member_id: uuid.UUID) -> None:
        """Soft-delete the seat. The marks it gave are untouched and stay in the tally."""
        JuryMemberModel.objects.filter(id=member_id).update(deleted_at=timezone.now())


class DjangoPerformanceScoringRepository:
    """Loads and stores each act's open/closed state."""

    def get(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID) -> PerformanceScoring | None:
        model = PerformanceScoringModel.objects.filter(
            competition_id=competition_id,
            submission_id=submission_id,
            deleted_at__isnull=True,
        ).first()
        return None if model is None else to_scoring(model)

    def by_competition(self, competition_id: uuid.UUID) -> tuple[PerformanceScoring, ...]:
        rows = PerformanceScoringModel.objects.filter(competition_id=competition_id, deleted_at__isnull=True).order_by("created_at")
        return tuple(to_scoring(model) for model in rows)

    def current(self, competition_id: uuid.UUID) -> PerformanceScoring | None:
        """The act the host has open.

        Most recently opened first, because opening a second act without closing the
        first is something a host does — two acts back to back, one announcer — and the
        later one is the one on stage.
        """
        model = (
            PerformanceScoringModel.objects.filter(
                competition_id=competition_id,
                status=PerformanceScoringStatus.OPEN.value,
                deleted_at__isnull=True,
            )
            .order_by("-opened_at")
            .first()
        )
        return None if model is None else to_scoring(model)

    def save(self, scoring: PerformanceScoring) -> None:
        PerformanceScoringModel.objects.update_or_create(id=scoring.id, defaults=scoring_to_model(scoring))


class DjangoScorecardRepository:
    """Loads and stores the panel's sheets."""

    def get(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID, jury_member_id: uuid.UUID) -> Scorecard | None:
        model = ScorecardModel.objects.filter(
            competition_id=competition_id,
            submission_id=submission_id,
            jury_member_id=jury_member_id,
            deleted_at__isnull=True,
        ).first()
        return None if model is None else to_scorecard(model)

    def by_submission(self, *, competition_id: uuid.UUID, submission_id: uuid.UUID) -> tuple[Scorecard, ...]:
        rows = ScorecardModel.objects.filter(
            competition_id=competition_id,
            submission_id=submission_id,
            deleted_at__isnull=True,
        ).order_by("created_at")
        return tuple(to_scorecard(model) for model in rows)

    def by_submissions(self, *, competition_id: uuid.UUID, submission_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, tuple[Scorecard, ...]]:
        """Every sheet for a batch of acts, in one query.

        The tally screen reckons a whole festival at once; one query per act would make
        a page of two hundred entries two hundred round trips.
        """
        if not submission_ids:
            return {}
        rows = ScorecardModel.objects.filter(
            competition_id=competition_id,
            submission_id__in=list(submission_ids),
            deleted_at__isnull=True,
        ).order_by("created_at")
        grouped: dict[uuid.UUID, list[Scorecard]] = {}
        for model in rows:
            grouped.setdefault(model.submission_id, []).append(to_scorecard(model))
        return {key: tuple(value) for key, value in grouped.items()}

    def by_member(self, *, competition_id: uuid.UUID, jury_member_id: uuid.UUID) -> tuple[Scorecard, ...]:
        rows = ScorecardModel.objects.filter(
            competition_id=competition_id,
            jury_member_id=jury_member_id,
            deleted_at__isnull=True,
        ).order_by("created_at")
        return tuple(to_scorecard(model) for model in rows)

    def save(self, scorecard: Scorecard) -> None:
        ScorecardModel.objects.update_or_create(id=scorecard.id, defaults=scorecard_to_model(scorecard))
