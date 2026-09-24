"""``DjangoJuryNotifier`` — the letter that seats somebody on a jury.

Concrete adapter for the :class:`~apps.judging.application.interfaces.JuryNotifier`
port over Django core mail. Mirrors the Applications, Identity and Results gateways: a
plain-text body plus an HTML alternative through the shared :mod:`apps.emailing`
template.

**Priority, not bulk.** This is the opposite case to a results letter: exactly one
person is waiting for exactly this message, usually shortly before a festival, and
until it arrives they cannot do the thing they were asked to do. It goes on the same
channel as a password reset because it is the same kind of letter.

There is no feed notification alongside it, deliberately. The recipient does not have
an account yet — that is what the link is for.
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.emailing import render_transactional_email_html
from apps.notifications.infrastructure.email import send_priority

__all__ = ["DjangoJuryNotifier"]

_SUBJECT = "Приглашение в жюри"


class DjangoJuryNotifier:
    """Jury invitation notifier (``JuryNotifier`` port), via Django core mail."""

    def __init__(self, *, from_email: str | None = None) -> None:
        self._from_email = from_email if from_email is not None else settings.DEFAULT_FROM_EMAIL
        self._base_url = settings.FRONTEND_BASE_URL.rstrip("/")

    def notify_jury_invited(
        self,
        *,
        email: str,
        full_name: str,
        competition_title: str,
        invitation_url: str,
    ) -> bool:
        """Send the invitation. Returns whether it was handed to the mail backend."""
        full_url = f"{self._base_url}{invitation_url}"
        body = (
            f"Здравствуйте, {full_name}!\n\n"
            f"Вас пригласили в состав жюри фестиваля «{competition_title}».\n\n"
            "Чтобы принять приглашение и получить доступ к оценке выступлений, "
            f"перейдите по ссылке:\n{full_url}\n\n"
            "Ссылка одноразовая: после того как вы её откроете и войдёте, она перестанет действовать.\n\n"
            "С уважением,\nКоманда «Взлёт талантов»"
        )
        html_body = render_transactional_email_html(
            title=_SUBJECT,
            intro=f"Здравствуйте, {full_name}! Вас пригласили в состав жюри фестиваля «{competition_title}».",
            details_label="Фестиваль",
            details=competition_title,
            button_label="Принять приглашение",
            button_url=full_url,
            status="info",
            status_label="Приглашение в жюри",
        )
        message = EmailMultiAlternatives(subject=_SUBJECT, body=body, from_email=self._from_email, to=[email])
        message.attach_alternative(html_body, "text/html")
        send_priority(message)
        return True
