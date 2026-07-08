"""Unit tests for the Django email gateway adapter.

Exercises :class:`DjangoEmailGateway` against Django's in-memory email backend
(``mail.outbox``, configured by the testing settings): a verification email is
built with the right sender, recipient, subject, and a body carrying the link.
No SMTP server and no database are involved; the SMTP→Mailhog path is exercised
by the running stack.
"""

from __future__ import annotations

from datetime import UTC, datetime

from django.core import mail

from apps.identity.domain.value_objects import Email, FullName, Locale
from apps.identity.infrastructure.messaging import DjangoEmailGateway


class TestDjangoEmailGateway:
    def test_sends_verification_email(self) -> None:
        gateway = DjangoEmailGateway(from_email="no-reply@vt.test")
        link = "https://frontend.test/verify-email?token=abc"

        gateway.send_verification_email(
            email=Email("recipient@example.com"),
            full_name=FullName.of("Ada", "Lovelace"),
            verification_url=link,
            locale=Locale.default(),
        )

        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.from_email == "no-reply@vt.test"
        assert message.to == ["recipient@example.com"]
        assert message.subject
        assert link in message.body

    def test_sends_password_reset(self) -> None:
        gateway = DjangoEmailGateway(from_email="no-reply@vt.test")
        link = "https://frontend.test/reset-password?token=xyz"

        gateway.send_password_reset(
            email=Email("recipient@example.com"),
            full_name=FullName.of("Ada", "Lovelace"),
            reset_url=link,
            expires_at=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
            locale=Locale.default(),
        )

        assert len(mail.outbox) == 1
        assert link in mail.outbox[0].body
