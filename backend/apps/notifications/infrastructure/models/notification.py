"""``NotificationModel`` — one entry in a person's cabinet notification feed.

Persistence only (ARCH-001 §7.2, §14). The row is deliberately flat and already
rendered: title, body and an optional in-app link, in the words the recipient will
read. It carries no reference to whatever produced it.

That is on purpose. A notification is a *message that was delivered*, not a view of
current state — the same reason the platform stores what an email said rather than
re-deriving it. "Заявка возвращена на исправление" stays true in the feed after the
applicant has fixed it and the entry has moved on; a feed rebuilt from live objects
would silently rewrite its own history, and the person would be told something they
were never told.

Reading is scoped to ``recipient_id`` and never to an id from a request, so one
account can never see another's feed.
"""

from __future__ import annotations

from django.db import models

from .base import BasePersistenceModel

__all__ = ["NotificationKind", "NotificationModel"]


class NotificationKind(models.TextChoices):
    """What happened. Drives the icon and accent the cabinet renders, nothing more.

    Kept coarse on purpose: the feed groups by what the reader must *do* — pay,
    fix something, or simply know — rather than by which use case emitted the row.
    New kinds are added here.
    """

    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED", "Application submitted"
    #: Separate from APPLICATION_SUBMITTED because nothing is being asked of the
    #: reader and nothing is owed: the entry is in a queue, and the next move is the
    #: organizer's. Reading it as "submitted" would have them waiting for an invoice.
    APPLICATION_WAITLISTED = "APPLICATION_WAITLISTED", "Application waitlisted"
    PAYMENT_EXPECTED = "PAYMENT_EXPECTED", "Payment expected"
    APPLICATION_CANCELLED = "APPLICATION_CANCELLED", "Application cancelled"
    APPLICATION_APPROVED = "APPLICATION_APPROVED", "Application approved"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED", "Correction requested"
    #: The organizer corrected the entry themselves instead of sending it back. Its
    #: own kind rather than CORRECTION_REQUESTED: nothing is being asked of the
    #: reader — they are being told what was changed on their behalf.
    APPLICATION_CORRECTED = "APPLICATION_CORRECTED", "Application corrected by organizer"
    FILES_REQUESTED = "FILES_REQUESTED", "Files requested"
    RESULTS_PUBLISHED = "RESULTS_PUBLISHED", "Results published"


class NotificationModel(BasePersistenceModel):
    """Database row for one notification (persistence only — no business logic)."""

    #: The Identity user this is addressed to. A plain UUID column, not a foreign
    #: key: the user lives in another bounded context and must never be joined across
    #: the boundary.
    recipient_id = models.UUIDField()

    kind = models.CharField(max_length=32, choices=NotificationKind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=2000, blank=True, default="")

    #: Where the cabinet should take the reader, as a frontend path
    #: (``/cabinet/applications/<id>``). A path rather than an absolute URL so the
    #: same row renders correctly whatever host the cabinet is served from.
    link = models.CharField(max_length=500, blank=True, default="")

    #: When the recipient opened it; ``None`` while unread. Not a boolean, because
    #: "when did they see this" is the question support actually asks.
    read_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta(BasePersistenceModel.Meta):
        db_table = "notifications_notification"
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        indexes = [
            *BasePersistenceModel.Meta.indexes,
            # The feed's only two queries: one person's newest entries, and how many
            # of them are unread.
            models.Index(fields=["recipient_id", "-created_at"]),
            models.Index(fields=["recipient_id", "read_at"]),
        ]
        constraints = [
            *BasePersistenceModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(kind__in=NotificationKind.values),
                name="notifications_notification_kind_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} → {self.recipient_id}"
