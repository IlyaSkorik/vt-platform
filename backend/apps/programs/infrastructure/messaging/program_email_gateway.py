"""``DjangoProgramNotifier`` — the letter that says the running order is up.

Concrete adapter for the :class:`~apps.programs.application.interfaces.ProgramNotifier`
port over Django core mail. Mirrors the Results gateway: a plain-text body plus an HTML
alternative through the shared :mod:`apps.emailing` template, and the same news written
into the cabinet feed beside it.

**Bulk, not priority.** Announcing a programme writes to every applicant in it at once —
a few hundred messages in a minute for a large festival, which is exactly the load the
second mailbox exists to absorb. Nobody is sitting at their inbox unable to proceed:
the link works whether or not the letter has landed, and putting this on the priority
channel would push a password reset behind three hundred running orders.

The letter leads with the participant's **own** lines. A programme is forty rows of
other people's numbers and one that matters to the reader, and «№14, 11:47» is the whole
of what they needed to be told; the link is there for the rest of the day.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.emailing import render_transactional_email_html
from apps.notifications.infrastructure import feed
from apps.notifications.infrastructure.email import send_bulk
from apps.notifications.infrastructure.models import NotificationKind
from apps.programs.application.rendering import day as _day

__all__ = ["DjangoProgramNotifier"]

_SUBJECT = "Программа опубликована"


class DjangoProgramNotifier:
    """Programme announcement notifier (``ProgramNotifier`` port), via Django core mail."""

    def __init__(self, *, from_email: str | None = None) -> None:
        self._from_email = from_email if from_email is not None else settings.DEFAULT_FROM_EMAIL
        self._base_url = settings.FRONTEND_BASE_URL.rstrip("/")

    def notify_program_published(
        self,
        *,
        user_id: UUID,
        email: str,
        applicant_name: str | None,
        competition_title: str | None,
        program_name: str,
        starts_at: datetime | None,
        slots: Sequence[tuple[str, str, str]],
        program_url: str,
        note: str | None,
    ) -> None:
        """Tell one applicant where and when their acts are, and where to read the rest."""
        greeting = f"Здравствуйте, {applicant_name}!" if applicant_name else "Здравствуйте!"
        scope = " · ".join(part for part in (competition_title, program_name) if part)
        when = _day(starts_at)
        # «№14, 11:47 — Катюша». The time is dropped rather than shown as a dash when the
        # programme has no start yet: the order is settled and the clock is not, and a
        # blank says that better than «—» beside a real number.
        lines = "\n".join(" — ".join(part for part in (f"№{number}" + (f", {time}" if time else ""), title) if part) for number, time, title in slots)
        full_url = f"{self._base_url}{program_url}"

        feed.publish(
            recipient_id=user_id,
            kind=NotificationKind.PROGRAM_PUBLISHED,
            title="Программа опубликована" + (f" — {scope}" if scope else ""),
            body=f"{lines}\n\nПолная программа — по ссылке из письма." + (f"\n\n{note}" if note else ""),
            link=program_url,
        )

        body = (
            f"{greeting}\n\n"
            f"Программа опубликована{f' — {scope}' if scope else ''}"
            f"{f'. Начало {when}' if when else ''}.\n\n"
            f"{'Ваши выступления:' if len(slots) > 1 else 'Ваше выступление:'}\n{lines}\n\n"
            + (f"{note}\n\n" if note else "")
            + f"Полная программа: {full_url}\n\n"
            "Порядок может измениться — перед выездом сверьтесь со ссылкой: она всегда показывает актуальную версию.\n\n"
            "С уважением,\nКоманда «Взлёт талантов»"
        )
        html_body = render_transactional_email_html(
            title=_SUBJECT,
            intro=(
                f"{greeting} Программа опубликована{f' — {scope}' if scope else ''}"
                f"{f'. Начало {when}' if when else ''}." + (f" {note}" if note else "")
            ),
            details_label="Ваши выступления" if len(slots) > 1 else "Ваше выступление",
            details=lines,
            button_label="Открыть программу",
            button_url=full_url,
            status="info",
            status_label="Программа опубликована",
        )

        message = EmailMultiAlternatives(subject=_SUBJECT, body=body, from_email=self._from_email, to=[email])
        message.attach_alternative(html_body, "text/html")
        send_bulk(message)
