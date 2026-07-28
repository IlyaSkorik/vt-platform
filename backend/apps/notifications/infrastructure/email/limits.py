"""The mail provider's per-mailbox quotas, enforced before a message leaves the platform.

These are contractual limits on the provider's servers (OPS-009), and every one of them
fails in a way the sender cannot see: a message over the size limit is refused, a message
with too many recipients is refused, and a burst over the rate limit is throttled or
dropped as suspected bulk mail. The organizer clicks "вернуть на исправление" for eighty
applications and hears nothing about it.

So the platform counts its own sends and refuses what the provider would refuse:

* **30 messages per minute per mailbox.** Counted in the shared cache, keyed by envelope
  sender, so the quota holds however many workers are running. A fixed one-minute window
  can in principle let a burst straddle the boundary; that is deliberate rather than
  overlooked - the recovery is the same retry that covers any refusal, and real traffic
  does not sit at the cap.
* **50 recipients per message**, counting To + Cc + Bcc together, which is how the
  provider counts them.
* **100 MB per message**, checked against the assembled MIME payload rather than the
  attachment bytes, since encoding inflates them by about a third.
"""

from __future__ import annotations

import math
import time
from email.message import Message

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage

__all__ = [
    "MessageTooLargeError",
    "QuotaExceededError",
    "TooManyRecipientsError",
    "message_size",
    "recipient_count",
    "reserve_send_slot",
    "seconds_until_window_resets",
    "validate_message",
]

_WINDOW_SECONDS = 60
#: A little longer than the window, so a key cannot expire while it is still being counted.
_KEY_TTL_SECONDS = _WINDOW_SECONDS * 2


class MailLimitError(Exception):
    """A message the mail provider would refuse."""


class MessageTooLargeError(MailLimitError):
    """Over the provider's per-message size limit."""


class TooManyRecipientsError(MailLimitError):
    """Over the provider's per-message recipient limit."""


class QuotaExceededError(MailLimitError):
    """This mailbox has used its allowance for the current minute."""


def recipient_count(message: EmailMessage) -> int:
    """Everyone the provider will count for this message."""
    return len(message.to or []) + len(message.cc or []) + len(message.bcc or [])


def message_size(message: EmailMessage) -> int:
    """The assembled message's size in bytes, as the provider will see it."""
    mime: Message = message.message()
    return len(mime.as_bytes())


def validate_message(message: EmailMessage) -> None:
    """Raise if the provider would refuse this message outright.

    Checked before anything is queued, so the caller finds out synchronously - a message
    that can never be delivered should not become a retrying background task.
    """
    recipients = recipient_count(message)
    limit = int(getattr(settings, "MAIL_MAX_RECIPIENTS", 50))
    if recipients > limit:
        raise TooManyRecipientsError(f"The message has {recipients} recipients; the provider allows {limit}.")

    size = message_size(message)
    max_bytes = int(getattr(settings, "MAIL_MAX_BYTES", 100 * 1024 * 1024))
    if size > max_bytes:
        raise MessageTooLargeError(f"The message is {size} bytes; the provider allows {max_bytes}.")


def _window_key(sender: str, *, now: float) -> str:
    return f"mail:quota:{sender or 'default'}:{int(now // _WINDOW_SECONDS)}"


def reserve_send_slot(sender: str, *, now: float | None = None) -> None:
    """Claim one of this mailbox's sends for the current minute.

    Raises :class:`QuotaExceededError` when the allowance is gone, which the delivery task
    turns into a retry rather than a failure - the message is fine, this minute is not.

    ``cache.incr`` on a key seeded by ``cache.add`` is the atomic pair here: ``add`` only
    succeeds for whoever gets there first, so two workers cannot both believe they created
    the window and reset each other's count.
    """
    limit = int(getattr(settings, "MAIL_RATE_LIMIT_PER_MINUTE", 30))
    if limit <= 0:
        return

    key = _window_key(sender, now=now if now is not None else time.time())
    if cache.add(key, 1, timeout=_KEY_TTL_SECONDS):
        used = 1
    else:
        try:
            used = cache.incr(key)
        except ValueError:
            # The key expired between `add` and `incr`; this send starts a fresh window.
            cache.set(key, 1, timeout=_KEY_TTL_SECONDS)
            used = 1

    if used > limit:
        raise QuotaExceededError(f"Mailbox {sender or 'default'} has used its {limit} sends for this minute.")


def seconds_until_window_resets(*, now: float | None = None) -> int:
    """How long to wait before the mailbox has a fresh allowance. At least one second."""
    moment = now if now is not None else time.time()
    return max(1, math.ceil(_WINDOW_SECONDS - (moment % _WINDOW_SECONDS)))
