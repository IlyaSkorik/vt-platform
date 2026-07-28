"""The one way out of the platform for mail, and the two channels it leaves by.

Every context composes its own messages - Identity writes the verification letter,
Applications writes the "returned for correction" one - and hands the finished message
here. Three things happen that cannot happen at a call site:

* the provider's per-message limits are checked **now**, so a message that can never be
  delivered fails where the caller can see it rather than becoming a retrying task;
* delivery moves to a worker, where the per-minute quota is counted and a refusal can be
  retried. Sending in the request cannot do either: an organizer returning eighty
  applications for correction would send eighty messages in a few seconds, and the
  provider treats that as bulk mail;
* the message is routed to one of two mailboxes.

**The split is not about importance, it is about what happens under load.** The provider
counts its allowance per mailbox, so:

* :func:`send_priority` - somebody is waiting to proceed: a verification link, a password
  reset, an invitation, a payment deadline. These must not queue behind anything.
* :func:`send_bulk` - a notice produced in batches: submission receipts during a
  registration rush, an organizer's review outcomes, the auto-cancellation sweep. Large,
  predictable, and nobody is staring at their inbox for one.

A second mailbox doubles the send rate; the priority carried with the task is what keeps
the first channel from waiting behind the second in the queue itself. Both are needed -
either alone leaves a password reset stuck behind five hundred receipts.

The queued payload is deliberately a small dict rather than a pickled message: it sits in
Redis until a worker picks it up, and a broker is the wrong place for megabytes.
"""

from __future__ import annotations

from typing import Any, Final

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives

from apps.notifications.infrastructure.email.limits import validate_message

__all__ = ["rebuild_message", "send_bulk", "send_priority", "serialize_message"]

_HTML = "text/html"

#: Celery priorities, matching the steps declared in settings. Higher runs first.
_PRIORITY: Final = 9
_BULK: Final = 3


def serialize_message(message: EmailMessage) -> dict[str, Any]:
    """Reduce a message to what a broker should carry."""
    if message.attachments:
        # Nothing in the platform emails attachments: documents are linked, not sent, so
        # they stay behind their own access rules and out of a 100 MB message limit. If that
        # ever changes, the bytes belong in storage with a link in the body - not in Redis.
        raise ValueError("Attachments are not supported for queued mail; link to the file instead.")
    html = next((content for content, mimetype in getattr(message, "alternatives", []) or [] if mimetype == _HTML), None)
    return {
        "subject": message.subject,
        "body": message.body,
        "html": html,
        "from_email": message.from_email,
        "to": list(message.to or []),
        "cc": list(message.cc or []),
        "bcc": list(message.bcc or []),
        "reply_to": list(message.reply_to or []),
    }


def rebuild_message(payload: dict[str, Any]) -> EmailMultiAlternatives:
    """The inverse of :func:`serialize_message`, run inside the worker."""
    message = EmailMultiAlternatives(
        subject=payload.get("subject", ""),
        body=payload.get("body", ""),
        from_email=payload.get("from_email") or None,
        to=payload.get("to") or [],
        cc=payload.get("cc") or [],
        bcc=payload.get("bcc") or [],
        reply_to=payload.get("reply_to") or [],
    )
    html = payload.get("html")
    if html:
        message.attach_alternative(html, _HTML)
    return message


def send_priority(message: EmailMessage) -> None:
    """Queue a message somebody is waiting on: a link, a reset, a deadline.

    Leaves by the first mailbox and jumps the queue, so a registration rush cannot delay
    somebody who cannot log in until this arrives.
    """
    _queue(message, priority=_PRIORITY)


def send_bulk(message: EmailMessage) -> None:
    """Queue a notice produced in batches: receipts, review outcomes, sweep results.

    Rewritten to leave by the second mailbox, which is what keeps its volume off the first
    one's allowance. Falls back to the same address when only one mailbox is configured.
    """
    message.from_email = str(getattr(settings, "MAIL_BULK_FROM", "") or message.from_email)
    _queue(message, priority=_BULK)


def _queue(message: EmailMessage, *, priority: int) -> None:
    """Validate against the provider's per-message limits, then hand over to a worker."""
    validate_message(message)
    # Imported here rather than at module scope: the task module needs this one for
    # rebuilding, and a top-level import either way would close the circle.
    from apps.notifications.tasks import deliver_email

    deliver_email.apply_async(args=[serialize_message(message)], priority=priority)
