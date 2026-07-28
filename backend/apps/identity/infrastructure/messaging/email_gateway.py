"""``DjangoEmailGateway`` — the transactional-email adapter over Django core mail.

Concrete implementation of the
:class:`~apps.identity.application.interfaces.EmailGateway` port (ARCH-001 §7.2,
§7.3). It is the single component that turns an application-layer request to
"email this person a verification / reset link" into an actual message handed to
Django's configured ``EMAIL_BACKEND`` — SMTP against Mailhog in local dev, a real
provider in production (see ``config/settings``). The application and domain
layers depend only on the port; swapping the transport changes only settings, not
a use case.

Contract (from the port): the gateway receives an **already-built** link and never
mints or sees the underlying token — secrets are the token service's concern. It
renders a localized subject/body, sets the envelope sender from
``DEFAULT_FROM_EMAIL``, and sends synchronously through the active backend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.emailing import render_transactional_email_html
from apps.identity.domain.value_objects import Email, FullName, Locale
from apps.notifications.infrastructure.email import send_priority

__all__ = ["DjangoEmailGateway"]

_VERIFICATION_SUBJECT: Final = "Подтвердите адрес электронной почты"
_RESET_SUBJECT: Final = "Восстановление пароля"


def _verification_body(*, full_name: FullName, verification_url: str) -> str:
    """Render the plain-text verification email body."""
    return (
        f"Здравствуйте, {full_name.first_name}!\n\n"
        "Благодарим за регистрацию на платформе «Взлёт талантов». "
        "Чтобы завершить регистрацию, подтвердите адрес электронной почты, "
        "перейдя по ссылке ниже:\n\n"
        f"{verification_url}\n\n"
        "Если вы не создавали учётную запись, просто проигнорируйте это письмо.\n\n"
        "С уважением,\nКоманда «Взлёт талантов»"
    )


def _format_expiry(expires_at: datetime) -> str:
    """Render a reset link's expiry as a human-readable local time.

    Formatted in the (already localized) zone the ``expires_at`` carries — e.g.
    ``19.07.2026 22:33 (MSK)`` — instead of a raw ISO-8601 string, which reads as
    an implementation detail to a recipient.
    """
    zone = expires_at.tzname() or "UTC"
    return f"{expires_at:%d.%m.%Y %H:%M} ({zone})"


def _reset_body(*, full_name: FullName, reset_url: str, expires_at: datetime) -> str:
    """Render the plain-text password-reset email body."""
    return (
        f"Здравствуйте, {full_name.first_name}!\n\n"
        "Мы получили запрос на восстановление пароля. "
        "Чтобы задать новый пароль, перейдите по ссылке ниже:\n\n"
        f"{reset_url}\n\n"
        f"Ссылка действительна до {_format_expiry(expires_at)}.\n\n"
        "Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.\n\n"
        "С уважением,\nКоманда «Взлёт талантов»"
    )


class DjangoEmailGateway:
    """Send transactional emails via Django core mail (``EmailGateway`` port).

    Stateless and cheap to construct. ``from_email`` overrides the envelope sender
    for tests; it defaults to ``settings.DEFAULT_FROM_EMAIL``. Structurally
    satisfies the port without inheriting it (the seam is structural by design).
    """

    def __init__(self, *, from_email: str | None = None) -> None:
        self._from_email = from_email if from_email is not None else settings.DEFAULT_FROM_EMAIL

    def send_verification_email(self, *, email: Email, full_name: FullName, verification_url: str, locale: Locale) -> None:
        """Send an email-ownership verification link to ``email``."""
        body = _verification_body(full_name=full_name, verification_url=verification_url)
        self._send(
            subject=_VERIFICATION_SUBJECT,
            body=body,
            html_body=render_transactional_email_html(
                title=_VERIFICATION_SUBJECT,
                intro=f"Здравствуйте, {full_name.first_name}! Благодарим за регистрацию на платформе «Взлет талантов».",
                details_label="Действие",
                details="Подтвердите адрес электронной почты, чтобы завершить регистрацию.",
                button_label="Подтвердить email",
                button_url=verification_url,
            ),
            to=email.value,
        )

    def send_password_reset(
        self,
        *,
        email: Email,
        full_name: FullName,
        reset_url: str,
        expires_at: datetime,
        locale: Locale,
    ) -> None:
        """Send a password-reset link to ``email``, valid until ``expires_at``."""
        body = _reset_body(full_name=full_name, reset_url=reset_url, expires_at=expires_at)
        self._send(
            subject=_RESET_SUBJECT,
            body=body,
            html_body=render_transactional_email_html(
                title=_RESET_SUBJECT,
                intro=f"Здравствуйте, {full_name.first_name}! Мы получили запрос на восстановление пароля.",
                details_label="Срок действия ссылки",
                details=f"Ссылка действительна до {_format_expiry(expires_at)}.",
                button_label="Сбросить пароль",
                button_url=reset_url,
            ),
            to=email.value,
        )

    def _send(self, *, subject: str, body: str, html_body: str, to: str) -> None:
        """Queue a single message, within the provider's per-mailbox allowance."""
        message = EmailMultiAlternatives(subject=subject, body=body, from_email=self._from_email, to=[to])
        message.attach_alternative(html_body, "text/html")
        send_priority(message)
