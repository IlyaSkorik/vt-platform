"""The one way out of the platform for transactional mail.

Every context composes its own messages - Identity writes the verification letter,
Applications writes the "returned for correction" one - and hands the finished message
here. Two things happen that cannot happen at a call site:

* the provider's per-message limits are checked **now**, so a message that can never be
  delivered fails where the caller can see it rather than becoming a retrying task;
* delivery moves to a worker, where the per-minute quota is counted and a refusal can be
  retried. Sending in the request cannot do either: an organizer returning eighty
  applications for correction would send eighty messages in a few seconds, and the
  provider treats that as bulk mail.

The queued payload is deliberately a small dict rather than a pickled message: it sits in
Redis until a worker picks it up, and a broker is the wrong place for megabytes.
"""

from __future__ import annotations

from typing import Any

from django.core.mail import EmailMessage, EmailMultiAlternatives

from apps.notifications.infrastructure.email.limits import validate_message

__all__ = ["rebuild_message", "send_transactional", "serialize_message"]

_HTML = "text/html"


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


def send_transactional(message: EmailMessage) -> None:
    """Validate the message against the provider's limits, then queue it for delivery."""
    validate_message(message)
    # Imported here rather than at module scope: the task module needs this one for
    # rebuilding, and a top-level import either way would close the circle.
    from apps.notifications.tasks import deliver_email

    deliver_email.delay(serialize_message(message))
