"""Background delivery of transactional mail.

One task per message, because the provider's allowance is counted in messages per minute.
Out of allowance is not a failure - the message is fine and this minute is not - so the task
comes back when the window resets rather than giving up.

Authentication failures are the one thing that must **not** be retried: ten in a minute and
the provider stops accepting connections from anywhere except the last IP that logged in
successfully (contract §5.7). A worker retrying a wrong password would lock the platform out
of its own mailbox, so it stops and says so loudly instead.
"""

from __future__ import annotations

import logging
from smtplib import SMTPAuthenticationError, SMTPException
from typing import Any

from celery import shared_task

from apps.notifications.infrastructure.email.delivery import rebuild_message
from apps.notifications.infrastructure.email.limits import (
    QuotaExceededError,
    reserve_send_slot,
    seconds_until_window_resets,
)

__all__ = ["deliver_email"]

logger = logging.getLogger(__name__)

#: Roughly two hours of trying at the backoff below - long enough to ride out a provider
#: hiccup, short enough that a message never arrives so late it confuses its recipient.
_MAX_RETRIES = 12
_MAX_BACKOFF_SECONDS = 600


# Celery ships no inline type information (mypy.ini declares it stub-less), so the
# decorator is untyped and would silently make every task function untyped too.
@shared_task(bind=True, name="notifications.deliver_email", max_retries=_MAX_RETRIES)  # type: ignore[untyped-decorator]
def deliver_email(self: Any, payload: dict[str, Any]) -> str:
    """Send one already-validated message, within this mailbox's allowance."""
    message = rebuild_message(payload)
    sender = message.from_email or ""

    try:
        reserve_send_slot(sender)
    except QuotaExceededError as exc:
        # Not an error worth logging at warning level: it is the limiter working. The wait
        # comes from the limiter, which knows when the earlier messages age out of the
        # sliding window - the next clock boundary is not the same thing.
        countdown = getattr(exc, "retry_after", None) or seconds_until_window_resets()
        logger.info("Mail quota reached for %s; retrying in %ss.", sender, countdown)
        raise self.retry(exc=exc, countdown=countdown) from exc

    try:
        message.send(fail_silently=False)
    except SMTPAuthenticationError:
        logger.exception(
            "SMTP rejected the credentials for %s. Not retrying: ten failed attempts in a "
            "minute and the provider will only accept the last successful IP.",
            sender,
        )
        return "auth-failed"
    except (SMTPException, OSError) as exc:
        countdown = min(_MAX_BACKOFF_SECONDS, 30 * 2**self.request.retries)
        logger.warning("Delivery to %s failed (%s); retrying in %ss.", message.to, exc, countdown)
        raise self.retry(exc=exc, countdown=countdown) from exc

    return "sent"
