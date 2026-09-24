"""Persistence for the panel and its work (persistence only, ARCH-001 §7.2).

Three tables, and the uniqueness constraints on them are where the fairness rules
become something the database enforces rather than something the application hopes for:
one seat per account per festival, one state row per act, one sheet per judge per act.

``user_id``, ``competition_id``, ``submission_id`` and the taxonomy ids are plain UUID
columns rather than foreign keys — cross-context references are held as ids (ARCH-001
§7.2), and a jury member's account lives in Identity.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["JuryMemberModel", "PerformanceScoringModel", "ScorecardModel"]


class JuryMemberModel(BasePersistenceModel):
    """Database row for one seat on one festival's jury."""

    competition_id = models.UUIDField()
    full_name = models.CharField(max_length=200)
    email = models.EmailField(max_length=320)
    title = models.CharField(max_length=200, null=True, blank=True, default=None)
    status = models.CharField(max_length=16, default="INVITED")
    user_id = models.UUIDField(null=True, blank=True, default=None)
    is_chair = models.BooleanField(default=False)
    #: The genres this member judges. An empty list means the whole festival.
    category_ids = models.JSONField(default=list)
    sort_order = models.PositiveIntegerField(default=0)
    invitation_token = models.CharField(max_length=128, null=True, blank=True, default=None, unique=True)
    invited_at = models.DateTimeField(null=True, blank=True, default=None)
    accepted_at = models.DateTimeField(null=True, blank=True, default=None)
    revoked_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "judging_jury_member"
        verbose_name = "jury member"
        verbose_name_plural = "jury members"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id", "sort_order"]),
            models.Index(fields=["user_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            # One seat per account per festival. Without this, an invitation opened
            # twice in two tabs seats the same person twice and their marks count twice.
            models.UniqueConstraint(
                fields=["competition_id", "user_id"],
                condition=models.Q(user_id__isnull=False),
                name="judging_unique_jury_member_account",
            ),
            models.UniqueConstraint(
                fields=["competition_id", "email"],
                name="judging_unique_jury_member_email",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name


class PerformanceScoringModel(BasePersistenceModel):
    """Database row for one act's open/closed state on the day."""

    competition_id = models.UUIDField()
    submission_id = models.UUIDField()
    status = models.CharField(max_length=16, default="PENDING")
    opened_at = models.DateTimeField(null=True, blank=True, default=None)
    closed_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "judging_performance_scoring"
        verbose_name = "performance scoring"
        verbose_name_plural = "performance scorings"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id", "status"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["competition_id", "submission_id"],
                name="judging_unique_performance_scoring",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.submission_id} — {self.status}"


class ScorecardModel(BasePersistenceModel):
    """Database row for one judge's sheet on one act."""

    competition_id = models.UUIDField()
    submission_id = models.UUIDField()
    jury_member_id = models.UUIDField()
    #: ``[{"criterion_id": "...", "score": "9.50"}, ...]`` — scores as strings, because
    #: a jury's arithmetic must round-trip exactly and JSON numbers are binary floats.
    scores = models.JSONField(default=list)
    comment = models.TextField(null=True, blank=True, default=None)
    submitted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "judging_scorecard"
        verbose_name = "scorecard"
        verbose_name_plural = "scorecards"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["competition_id", "submission_id"]),
            models.Index(fields=["competition_id", "jury_member_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["submission_id", "jury_member_id"],
                name="judging_unique_scorecard",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.jury_member_id} → {self.submission_id}"
