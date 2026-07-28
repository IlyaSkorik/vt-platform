"""Queueing the letters the organizer's review actions send.

These are the only messages the platform composes at the edge rather than in a gateway,
because they are about what an organizer just did to a batch of performances - text no
domain object owns. They are also the clearest case of bulk mail in the platform: returning
eighty applications for correction is one click and eighty applicants to tell.

So they leave by the bulk channel - its own mailbox, its own allowance, and behind anything
somebody is actually waiting on.
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.notifications.infrastructure.email import send_bulk

__all__ = ["queue_review_email"]


def queue_review_email(*, subject: str, body: str, to: str, html_body: str) -> None:
    """Compose one review-outcome message and hand it to the bulk delivery channel."""
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    message.attach_alternative(html_body, "text/html")
    send_bulk(message)
