"""The mail provider's per-mailbox quotas, enforced before a message leaves the platform.

These are contractual limits on the provider's servers (OPS-009), and every one of them
fails in a way the sender cannot see: a message over the size limit is refused, a message
with too many recipients is refused, and a burst over the rate limit is throttled or
dropped as suspected bulk mail. The organizer clicks "вернуть на исправление" for eighty
applications and hears nothing about it.

So the platform counts its own sends and refuses what the provider would refuse:

* **30 messages per minute per mailbox.** One counter per second in the shared cache, keyed
  by envelope sender, summed over the last sixty-one - so the quota holds however many
  workers are running, and it holds for a *rolling* minute rather than a clock one.

  Both simpler versions were tried and measured. A counter per minute hands out a fresh
  allowance the moment the clock turns over: queueing 41 messages at once put all 41 inside
  one rolling minute, 37% over the contract. Weighting the previous minute's count by how
  much of it is still in view fixes that and introduces the opposite error - it under-counts
  a burst that arrived late in the window, and a simulation catches it exceeding the limit
  too. Per-second counters are exact to the second at the cost of one ``incr`` and one
  ``get_many`` per message.
* **50 recipients per message**, counting To + Cc + Bcc together, which is how the
  provider counts them.
* **100 MB per message**, checked against the assembled MIME payload rather than the
  attachment bytes, since encoding inflates them by about a third.
"""

from __future__ import annotations

import math
import time
from contextlib import suppress
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
#: One bucket more than the window is wide.
#:
#: Counts are bucketed by whole second, so without the extra one a send at 12:00:00.9
#: followed by another at 12:01:00.1 sits in different buckets while being 59.2 s apart -
#: measured, and it let a 31st message through against an allowance of 30. The extra bucket
#: costs at most one message of headroom and makes the true rolling minute safe.
_BUCKETS = _WINDOW_SECONDS + 1
#: A little longer than the window, so a key cannot expire while it is still being counted.
_KEY_TTL_SECONDS = _WINDOW_SECONDS * 2


class MailLimitError(Exception):
    """A message the mail provider would refuse."""


class MessageTooLargeError(MailLimitError):
    """Over the provider's per-message size limit."""


class TooManyRecipientsError(MailLimitError):
    """Over the provider's per-message recipient limit."""


class QuotaExceededError(MailLimitError):
    """This mailbox has used its allowance for the moment.

    Carries ``retry_after``: how long until the sliding window has room again. The delivery
    task schedules its retry from this rather than guessing, because the answer depends on
    when the earlier messages went out, not on where the clock happens to be.
    """

    def __init__(self, message: str, *, retry_after: int) -> None:
        super().__init__(message)
        self.retry_after = retry_after


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


def _second_key(sender: str, second: int) -> str:
    return f"mail:quota:{sender or 'default'}:{second}"


def _take(key: str) -> int:
    """Add one to a second's count and return the new total.

    ``cache.incr`` on a key seeded by ``cache.add`` is the atomic pair: ``add`` only succeeds
    for whoever gets there first, so two workers cannot both believe they opened the second
    and reset each other's count.
    """
    if cache.add(key, 1, timeout=_KEY_TTL_SECONDS):
        return 1
    try:
        return int(cache.incr(key))
    except ValueError:
        # Expired between `add` and `incr`; this send opens a fresh second.
        cache.set(key, 1, timeout=_KEY_TTL_SECONDS)
        return 1


def reserve_send_slot(sender: str, *, now: float | None = None) -> None:
    """Claim one of this mailbox's sends, if the last sixty seconds leave room for it.

    Raises :class:`QuotaExceededError` when they do not, which the delivery task turns into a
    retry rather than a failure - the message is fine, this moment is not.

    One counter per second, summed over the last sixty. That is more keys than a
    window-per-minute counter and worth every one of them: a per-window counter hands out a
    fresh allowance the instant the clock turns over, which measurably put 41 messages inside
    one rolling minute against a limit of 30. Weighting the previous window instead only
    trades that for the opposite error - it under-counts a burst that arrived late in the
    window, and a simulation catches it exceeding the limit too. Counting seconds is exact to
    the second, and the cost is one ``incr`` plus one ``get_many`` per message.
    """
    limit = int(getattr(settings, "MAIL_RATE_LIMIT_PER_MINUTE", 30))
    if limit <= 0:
        return

    moment = now if now is not None else time.time()
    second = int(moment)
    key = _second_key(sender, second)
    _take(key)

    window = [second - offset for offset in range(_BUCKETS)]
    counts = cache.get_many([_second_key(sender, each) for each in window])
    used = sum(int(value or 0) for value in counts.values())

    if used > limit:
        # Give the slot back, or a task that keeps retrying would eat the allowance it waits
        # for. ValueError means the key already expired: nothing to give back.
        with suppress(ValueError):
            cache.decr(key)
        mailbox = sender or "default"
        raise QuotaExceededError(
            f"Mailbox {mailbox} has sent {used - 1} in the last {_WINDOW_SECONDS}s; the allowance is {limit}.",
            retry_after=_seconds_until_room(sender=sender, second=second, limit=limit),
        )


def _seconds_until_room(*, sender: str, second: int, limit: int) -> int:
    """How long until enough of the earlier sends age out, in whole seconds (at least one).

    Derived from when those sends actually happened rather than from the clock: the oldest
    ones inside the window are the ones whose leaving makes room, and waiting for a round
    minute is not the same thing.
    """
    oldest_first = [second - offset for offset in reversed(range(_BUCKETS))]
    counts = cache.get_many([_second_key(sender, each) for each in oldest_first])

    needed = 1
    for each in oldest_first:
        count = int(counts.get(_second_key(sender, each)) or 0)
        if not count:
            continue
        needed -= count
        if needed <= 0:
            # Once this second drops out of the counted buckets there is room again.
            return max(1, each + _BUCKETS - second)
    return _WINDOW_SECONDS


def seconds_until_window_resets(*, now: float | None = None) -> int:
    """How long to wait before the mailbox has a fresh allowance. At least one second."""
    moment = now if now is not None else time.time()
    return max(1, math.ceil(_WINDOW_SECONDS - (moment % _WINDOW_SECONDS)))
