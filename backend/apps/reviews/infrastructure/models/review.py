"""Persistence for the Reviews context: the page, and the notes left on it.

Two tables, mirroring the two aggregates. The page is one row per organization and
is rewritten in place; notes are appended by strangers and never updated.

Cross-context references (``organization_id``, ``competition_id``) are id-only
``UUIDField`` columns and never foreign keys (ARCH-001 §9.2). ``competition_title``
sits beside the id deliberately: a note has to keep saying which festival it was
about after that festival is renamed or deleted, and a title resolved by join at
read time would quietly rewrite what somebody wrote.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["ReviewModel", "ReviewPageModel"]


class ReviewPageModel(BasePersistenceModel):
    """Database row for one organization's review page (persistence only)."""

    organization_id = models.UUIDField()
    # The only credential the public page has. Unique platform-wide and permanent:
    # it is printed on a banner, and a banner is not reissued because a column was.
    slug = models.CharField(max_length=64)
    title = models.CharField(max_length=200)
    intro = models.TextField(blank=True, default="")
    # Whether the link still takes notes. Off, the page still answers and says so.
    accepting = models.BooleanField(default=True)

    class Meta(BasePersistenceModel.Meta):
        db_table = "reviews_page"
        verbose_name = "review page"
        verbose_name_plural = "review pages"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            models.Index(fields=["organization_id"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            # Unconditional, as in Voting: a revoked link must never be minted again
            # for something else, so the slug stays claimed even after a soft delete.
            models.UniqueConstraint(fields=["slug"], name="reviews_page_slug_unique"),
            # One page per organization. Partial, so a soft-deleted page does not
            # block the organization from ever having one again.
            models.UniqueConstraint(
                fields=["organization_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="reviews_page_unique_per_organization",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} (/{self.slug})"


class ReviewModel(BasePersistenceModel):
    """Database row for one note left through a public page (persistence only).

    The three ``consent_*`` columns are not audit decoration: they are the basis on
    which the name, the words and the photographs may be held at all (LEGAL-001
    §13.3). All three are non-null, and the domain will not build a review without
    them — a row here without a consent would be a row the platform cannot justify
    keeping. Code *and* version, as everywhere else on the platform: the code says
    what was agreed to, the version says which wording of it.
    """

    page = models.ForeignKey("reviews.ReviewPageModel", on_delete=models.CASCADE, related_name="reviews")
    # Denormalized from the page: every read is scoped by organization, and the
    # operator's console spans them, so this saves a join on the only two queries
    # this table has.
    organization_id = models.UUIDField()

    # Blank is the ordinary case: signing is optional, and an unsigned note is a
    # whole note. Stored NULL rather than "" so "unsigned" is one value, not two.
    author_name = models.CharField(max_length=120, null=True, blank=True, default=None)
    text = models.TextField()
    # Storage references, in the order they were attached. A list of keys rather
    # than a child table: they are written once, read whole, and never queried.
    photos = models.JSONField(default=list, blank=True)

    competition_id = models.UUIDField(null=True, blank=True, default=None)
    competition_title = models.CharField(max_length=300, blank=True, default="")

    consent_code = models.CharField(max_length=64)
    consent_version = models.CharField(max_length=64)
    consent_accepted_at = models.DateTimeField()
    submitted_at = models.DateTimeField()

    class Meta(BasePersistenceModel.Meta):
        db_table = "reviews_review"
        verbose_name = "review"
        verbose_name_plural = "reviews"
        ordering = ["-submitted_at"]
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            # The organizer's list: this organization's notes, newest first.
            models.Index(fields=["organization_id", "-submitted_at"]),
            models.Index(fields=["page", "-submitted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.author_name or 'без подписи'}: {self.text[:40]}"
