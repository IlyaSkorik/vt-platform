"""``DjangoResultsNotifier`` - the letter that says the results are in.

Concrete adapter for the :class:`~apps.results.application.interfaces.ResultsNotifier`
port over Django core mail. Mirrors the Applications and Identity gateways: a plain-text
body plus an HTML alternative rendered through the shared :mod:`apps.emailing` template.

**Bulk, not priority.** Publishing a nomination sends one letter per applicant, and a
festival publishes several nominations in an afternoon - a few hundred messages in a few
minutes, which is exactly the load the second mailbox exists to absorb. Nobody is sitting
at their inbox unable to proceed until this arrives: the diploma is already in their
cabinet and the protocol is already on the page, and the letter is what tells them to go
and look. Putting it on the priority channel would push a password reset behind three
hundred congratulations.

One letter carries **all** of an applicant's results in that nomination. A studio that
entered thirty acts gets one message listing thirty lines, which is both what a human
wants to read and the difference between one message and thirty against a provider that
counts its allowance per minute.
"""

from __future__ import annotations

from collections.abc import Sequence

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.emailing import render_transactional_email_html
from apps.notifications.infrastructure import feed
from apps.notifications.infrastructure.email import send_bulk
from apps.notifications.infrastructure.models import NotificationKind

__all__ = ["DjangoResultsNotifier"]

_SUBJECT = "Итоги подведены"


class DjangoResultsNotifier:
    """Results email notifier (``ResultsNotifier`` port), via Django core mail."""

    def __init__(self, *, from_email: str | None = None) -> None:
        self._from_email = from_email if from_email is not None else settings.DEFAULT_FROM_EMAIL
        self._base_url = settings.FRONTEND_BASE_URL.rstrip("/")
        self._documents_url = f"{self._base_url}/cabinet/documents"

    def notify_results_published(
        self,
        *,
        user_id: str,
        email: str,
        applicant_name: str | None,
        competition_title: str | None,
        nomination_title: str | None,
        results: Sequence[tuple[str, str]],
        protocol_url: str,
    ) -> None:
        """Tell one applicant their results, and where the diploma and protocol are."""
        greeting = f"Здравствуйте, {applicant_name}!" if applicant_name else "Здравствуйте!"
        scope = " · ".join(part for part in (competition_title, nomination_title) if part)
        lines = "\n".join(f"— {title}: {award}" for title, award in results)
        full_protocol_url = f"{self._base_url}{protocol_url}"

        # The same news in the cabinet. Results letters go out per nomination during a
        # festival's closing hours, which is exactly when an inbox is least reliable and
        # a participant is most likely to go looking for the answer themselves.
        feed.publish(
            recipient_id=user_id,
            kind=NotificationKind.RESULTS_PUBLISHED,
            title="Результаты опубликованы" + (f" — {scope}" if scope else ""),
            body=f"{lines}\n\nЭлектронный диплом доступен в разделе «Мои документы».",
            link="/cabinet/documents",
        )

        body = (
            f"{greeting}\n\n"
            f"Итоги подведены{f' — {scope}' if scope else ''}.\n\n"
            f"Ваши результаты:\n{lines}\n\n"
            "Электронный диплом доступен в личном кабинете, в разделе «Мои документы».\n"
            f"Протокол опубликован: {full_protocol_url}\n\n"
            "С уважением,\nКоманда «Взлёт талантов»"
        )
        html_body = render_transactional_email_html(
            title=_SUBJECT,
            intro=f"{greeting} Итоги подведены{f' — {scope}' if scope else ''}. Электронный диплом уже в личном кабинете.",
            details_label="Ваши результаты",
            details=lines,
            # The cabinet, not the protocol: the diploma is the thing this letter is
            # actually about, and the protocol link is in the body for whoever wants the
            # whole nomination.
            button_label="Мои документы",
            button_url=self._documents_url,
            status="success",
            status_label="Итоги подведены",
        )

        message = EmailMultiAlternatives(subject=_SUBJECT, body=body, from_email=self._from_email, to=[email])
        message.attach_alternative(html_body, "text/html")
        send_bulk(message)
