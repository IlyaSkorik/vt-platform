"""Queueing the letters the organizer's review actions send.

These are the only messages the platform composes at the edge rather than in a gateway,
because they are about what an organizer just did to a batch of performances - text no
domain object owns. They are also the ones most likely to arrive in a burst: returning
eighty applications for correction is one click and eighty applicants to tell.

So they go through the same queue as everything else, which is what keeps that burst inside
the provider's 30-messages-a-minute allowance instead of looking like bulk mail.
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.notifications.infrastructure.email import send_transactional

__all__ = ["queue_transactional_email"]


def queue_transactional_email(*, subject: str, body: str, to: str, html_body: str) -> None:
    """Compose one message to one recipient and hand it to the delivery queue."""
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    message.attach_alternative(html_body, "text/html")
    send_transactional(message)
