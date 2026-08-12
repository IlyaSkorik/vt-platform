"""``DjangoApplicantNotifier`` — telling an applicant what happened to their order.

Concrete adapter for the :class:`~apps.applications.application.interfaces.
ApplicantNotifier` port. Each notice goes out on **both** channels the platform has:

* a letter, over Django core mail (SMTP against Mailhog in dev, a real provider in
  prod) — a plain-text body plus an HTML alternative rendered through the shared
  :mod:`apps.emailing` template, mirroring the Identity gateway;
* an entry in the applicant's cabinet feed, over
  :mod:`apps.notifications.infrastructure.feed`.

Both, not either. Mail is how somebody finds out without looking, and it is also
what gets filtered, mislaid, or sent to an address they stopped reading; the cabinet
is where they go when they suspect they missed something. Writing both here rather
than at the call site keeps the wording of the two in one place — a letter and a
feed entry that disagree about what happened are worse than one channel.

The application layer depends only on the port; the transport is a settings concern.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives

from apps.emailing import render_transactional_email_html
from apps.notifications.infrastructure import feed
from apps.notifications.infrastructure.email import send_bulk, send_priority
from apps.notifications.infrastructure.models import NotificationKind

__all__ = ["DjangoApplicantNotifier"]

#: Which channel a letter leaves by — see ``apps.notifications.infrastructure.email``.
Deliver = Callable[[EmailMessage], None]

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

    @staticmethod
    def _cabinet_link(application_id: str) -> str:
        """Where the feed entry takes the reader: their own card for this order."""
        return f"/cabinet/applications/{application_id}"

    def notify_application_submitted(self, *, user_id: str, email: str, applicant_name: str, application_id: str) -> None:
        feed.publish(
            recipient_id=user_id,
            kind=NotificationKind.APPLICATION_SUBMITTED,
            title="Заявка подана",
            body="Мы получили вашу заявку вместе с квитанцией об оплате.",
            link=self._cabinet_link(application_id),
        )
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
                status="success",
                status_label="Заявка принята",
            ),
            to=email,
            # A receipt. During a registration rush these arrive by the hundred and nobody
            # is waiting on one, so they must not crowd out a password reset.
            deliver=send_bulk,
        )

    def notify_application_awaiting_payment(self, *, user_id: str, email: str, applicant_name: str, application_id: str, deadline: datetime) -> None:
        deadline_text = _format_deadline(deadline)
        feed.publish(
            recipient_id=user_id,
            kind=NotificationKind.PAYMENT_EXPECTED,
            title="Заявка подана — ожидается оплата",
            body=f"Прикрепите квитанцию об оплате до {deadline_text}, иначе заявка автоматически отменится.",
            link=self._cabinet_link(application_id),
        )
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
                details=(f"{deadline_text}. Прикрепите квитанцию об оплате до этого срока, иначе заявка автоматически отменится."),
                button_label="Прикрепить квитанцию",
                button_url=self._applications_url,
                status="warning",
                status_label="Ожидает оплаты",
            ),
            to=email,
            # Carries a deadline the applicant loses their place by missing. Late is the
            # same as never here, so it goes out on the priority channel.
            deliver=send_priority,
        )

    def notify_application_auto_cancelled(self, *, user_id: str, email: str, applicant_name: str, application_id: str) -> None:
        feed.publish(
            recipient_id=user_id,
            kind=NotificationKind.APPLICATION_CANCELLED,
            title="Заявка автоматически отменена",
            body="Квитанция об оплате не была прикреплена в срок. Пока открыта регистрация, можно подать новую заявку.",
            link=self._cabinet_link(application_id),
        )
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
                status="danger",
                status_label="Отменена",
            ),
            to=email,
            # Produced by the sweep, which cancels every overdue order in one pass. The
            # deadline has already gone by, so nothing is gained by arriving first.
            deliver=send_bulk,
        )

    def _send(self, *, subject: str, body: str, html_body: str, to: str, deliver: Deliver) -> None:
        """Queue a single message on the channel the caller chose."""
        message = EmailMultiAlternatives(subject=subject, body=body, from_email=self._from_email, to=[to])
        message.attach_alternative(html_body, "text/html")
        deliver(message)
