"""The one way into a person's cabinet notification feed.

Every context composes its own messages — Applications writes "заявка возвращена на
исправление", Results writes "результаты опубликованы" — and hands the finished text
here, exactly as it already hands finished email to
:mod:`apps.notifications.infrastructure.email`. This is the second channel beside
that one, and it is called from the same places for the same events: a letter can be
missed, filtered or sent to an address the person no longer reads, and the cabinet is
where they go to check.

:func:`publish` **never raises**. A feed entry is a copy of something the platform is
already telling the person by mail; failing an applicant's submit because the copy
could not be written would trade the thing that matters for the thing that does not.

The read helpers are here rather than behind a repository because the feed has no
aggregate: a notification is an immutable line of text plus the moment it was opened,
and everything asked of it is a query over one person's rows.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from typing import Final

from django.utils import timezone

from apps.notifications.infrastructure.models import NotificationKind, NotificationModel

__all__ = ["mark_all_read", "mark_read", "publish", "recent_for", "unread_count_for"]

_logger: Final = logging.getLogger(__name__)

#: How many entries the cabinet feed returns at most. The feed is a prompt to go and
#: look at something, not an archive: past a couple of hundred rows nobody scrolls,
#: and the older entries are about competitions that finished.
_MAX_FEED = 200


def _as_uuid(value: object) -> uuid.UUID | None:
    """Read ``value`` as a UUID, or ``None`` if it is not one.

    Recipient ids arrive from other contexts as strings or as domain value objects;
    a value that is not an identifier at all means there is nobody to notify, which
    is a skipped write rather than an error.
    """
    try:
        return uuid.UUID(str(value).strip())
    except (ValueError, AttributeError, TypeError):
        return None


def publish(
    *,
    recipient_id: object,
    kind: NotificationKind | str,
    title: str,
    body: str = "",
    link: str = "",
) -> None:
    """Add one entry to ``recipient_id``'s feed. Never raises."""
    try:
        recipient = _as_uuid(recipient_id)
        if recipient is None or not title.strip():
            return
        NotificationModel.objects.create(
            recipient_id=recipient,
            kind=str(kind.value if isinstance(kind, NotificationKind) else kind),
            title=title.strip()[:200],
            body=body.strip()[:2000],
            link=link.strip()[:500],
        )
    except Exception:
        _logger.warning("Could not publish a notification to %s", recipient_id, exc_info=True)


def recent_for(recipient_id: uuid.UUID, *, limit: int = _MAX_FEED) -> Sequence[NotificationModel]:
    """The recipient's newest entries, unread and read alike, newest first."""
    capped = max(1, min(limit, _MAX_FEED))
    return list(NotificationModel.objects.filter(recipient_id=recipient_id, deleted_at__isnull=True).order_by("-created_at")[:capped])


def unread_count_for(recipient_id: uuid.UUID) -> int:
    """How many of the recipient's entries are still unopened."""
    return NotificationModel.objects.filter(recipient_id=recipient_id, deleted_at__isnull=True, read_at__isnull=True).count()


def mark_read(recipient_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
    """Mark one entry read; ``False`` if it is not this recipient's, or already read.

    Scoped by recipient in the filter itself, so an id guessed from another account's
    feed matches nothing rather than being marked.
    """
    now = timezone.now()
    updated = NotificationModel.objects.filter(
        pk=notification_id,
        recipient_id=recipient_id,
        deleted_at__isnull=True,
        read_at__isnull=True,
    ).update(read_at=now, updated_at=now)
    return updated > 0


def mark_all_read(recipient_id: uuid.UUID) -> int:
    """Mark every unread entry of this recipient read; returns how many were."""
    now = timezone.now()
    return NotificationModel.objects.filter(recipient_id=recipient_id, deleted_at__isnull=True, read_at__isnull=True).update(
        read_at=now, updated_at=now
    )
