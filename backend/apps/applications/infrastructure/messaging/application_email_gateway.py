"""``DjangoApplicantNotifier`` — transactional emails about an order's lifecycle.

Concrete adapter for the :class:`~apps.applications.application.interfaces.
ApplicantNotifier` port over Django core mail (SMTP against Mailhog in dev, a real
provider in prod). Mirrors the Identity email gateway: a plain-text body plus an
HTML alternative rendered through the shared :mod:`apps.emailing` template. The
application layer depends only on the port; the transport is a settings concern.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.emailing import render_transactional_email_html

__all__ = ["DjangoApplicantNotifier"]

_SUBMITTED_SUBJECT: Final = "Заявка подана"
_AWAITING_PAYMENT_SUBJECT: Final = "Заявка подана — ожидается оплата"
_CANCELLED_SUBJECT: Final = "Заявка отменена"

#: Deadlines are shown to applicants in Minsk local time, not the stored UTC.
_DISPLAY_TZ: Final = ZoneInfo("Europe/Minsk")


def _format_deadline(deadline: datetime) -> str:
    """Render the payment deadline in Minsk local time (e.g. ``24.07.2026 22:17 (Мск)``)."""
    return f"{deadline.astimezone(_DISPLAY_TZ):%d.%m.%Y %H:%M} (Мск)"


class DjangoApplicantNotifier:
    """Applicant email notifier (``ApplicantNotifier`` port), via Django core mail."""

    def __init__(self, *, from_email: str | None = None) -> None:
        self._from_email = from_email if from_email is not None else settings.DEFAULT_FROM_EMAIL
        self._applications_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/cabinet/applications"

    def notify_application_submitted(self, *, email: str, applicant_name: str) -> None:
        body = (
            f"Здравствуйте, {applicant_name}!\n\n"
            "Ваша заявка успешно подана. Мы получили её вместе с квитанцией об оплате.\n\n"
            "С уважением,\nКоманда «Взлёт талантов»"
        )
        self._send(
            subject=_SUBMITTED_SUBJECT,
            body=body,
            html_body=render_transactional_email_html(
                title=_SUBMITTED_SUBJECT,
                intro=f"Здравствуйте, {applicant_name}! Ваша заявка успешно подана.",
                details_label="Статус",
                details="Заявка получена вместе с квитанцией об оплате.",
                button_label="Мои заявки",
                button_url=self._applications_url,
            ),
            to=email,
        )

    def notify_application_awaiting_payment(self, *, email: str, applicant_name: str, deadline: datetime) -> None:
        deadline_text = _format_deadline(deadline)
        body = (
            f"Здравствуйте, {applicant_name}!\n\n"
            "Ваша заявка подана. Пожалуйста, оплатите её и прикрепите квитанцию "
            f"до {deadline_text}.\n\n"
            "Если квитанция не будет прикреплена в срок, заявка автоматически отменится.\n\n"
            "С уважением,\nКоманда «Взлёт талантов»"
        )
        self._send(
            subject=_AWAITING_PAYMENT_SUBJECT,
            body=body,
            html_body=render_transactional_email_html(
                title=_AWAITING_PAYMENT_SUBJECT,
                intro=f"Здравствуйте, {applicant_name}! Ваша заявка подана и ожидает оплаты.",
                details_label="Оплатите до",
                details=(
                    f"{deadline_text}. Прикрепите квитанцию об оплате до этого срока, "
                    "иначе заявка автоматически отменится."
                ),
                button_label="Прикрепить квитанцию",
                button_url=self._applications_url,
            ),
            to=email,
        )

    def notify_application_auto_cancelled(self, *, email: str, applicant_name: str) -> None:
        body = (
            f"Здравствуйте, {applicant_name}!\n\n"
            "Ваша заявка автоматически отменена: квитанция об оплате не была прикреплена в срок.\n\n"
            "Вы можете подать новую заявку, пока открыта регистрация.\n\n"
            "С уважением,\nКоманда «Взлёт талантов»"
        )
        self._send(
            subject=_CANCELLED_SUBJECT,
            body=body,
            html_body=render_transactional_email_html(
                title=_CANCELLED_SUBJECT,
                intro=f"Здравствуйте, {applicant_name}! Ваша заявка автоматически отменена.",
                details_label="Причина",
                details="Квитанция об оплате не была прикреплена в срок.",
                button_label="Мои заявки",
                button_url=self._applications_url,
            ),
            to=email,
        )

    def _send(self, *, subject: str, body: str, html_body: str, to: str) -> None:
        message = EmailMultiAlternatives(subject=subject, body=body, from_email=self._from_email, to=[to])
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
