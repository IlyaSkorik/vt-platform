"""``DjangoOrganizerNotifier`` — the letter that says an accepted entry has changed.

Concrete adapter for the :class:`~apps.applications.application.interfaces.
OrganizerNotifier` port, built the same way as the applicant gateway next to it: a
plain-text body plus an HTML alternative through the shared :mod:`apps.emailing`
template.

It goes out on the **bulk** channel. Nobody is waiting on it — by the time it is
composed the edit has already been saved and the applicant has moved on — and during
a registration rush these arrive in numbers, so they must not queue ahead of a
password reset (see ``apps.notifications.infrastructure.email``).

One letter carries a whole editing session, not one change: the sweep that calls this
hands over every edit the applicant made since the last notice.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.emailing import render_transactional_email_html
from apps.notifications.infrastructure.email import send_bulk

__all__ = ["DjangoOrganizerNotifier"]

_REVISED_SUBJECT: Final = "В поданную заявку внесены изменения"

#: Organizers read times in Minsk local time, not the stored UTC.
_DISPLAY_TZ: Final = ZoneInfo("Europe/Minsk")

#: How many change lines one letter spells out before summarising the rest. A letter
#: is a prompt to go and look, not a substitute for the application itself.
_MAX_LISTED_CHANGES: Final = 15


class DjangoOrganizerNotifier:
    """Organizer email notifier (``OrganizerNotifier`` port), via Django core mail."""

    def __init__(self, *, from_email: str | None = None) -> None:
        self._from_email = from_email if from_email is not None else settings.DEFAULT_FROM_EMAIL
        self._base_url = settings.FRONTEND_BASE_URL.rstrip("/")

    def notify_application_revised(
        self,
        *,
        emails: Sequence[str],
        competition_title: str,
        applicant_name: str,
        application_id: str,
        changes: Sequence[str],
        revised_at: datetime,
    ) -> None:
        if not emails:
            return
        listed = list(changes[:_MAX_LISTED_CHANGES])
        hidden = len(changes) - len(listed)
        lines = [f"— {change}" for change in listed]
        if hidden > 0:
            lines.append(f"…и ещё изменений: {hidden}")
        details = "\n".join(lines) or "Состав заявки изменён."
        when = f"{revised_at.astimezone(_DISPLAY_TZ):%d.%m.%Y %H:%M} (Мск)"
        number = application_id[:8].upper()
        # The organizer's own workspace, not the applicant's cabinet. Deep-linked by
        # search rather than by queue: which queue a revised order sits in depends on
        # its status *and* whether a receipt is attached, so a queue in the URL would
        # sometimes open on an empty tab. The number is searchable (the workspace
        # matches it), which is stable whatever the order's state.
        link = f"{self._base_url}/staff/applications?q={number}"

        body = (
            f"Заявка №{number} на фестиваль «{competition_title}» была изменена после подачи.\n\n"
            f"Заявитель: {applicant_name}\n"
            f"Последнее изменение: {when}\n\n"
            f"Что изменилось:\n{details}\n\n"
            f"Открыть заявку: {link}\n\n"
            "С уважением,\nКоманда «Взлёт талантов»"
        )
        html_body = render_transactional_email_html(
            title=_REVISED_SUBJECT,
            intro=(f"Заявка №{number} на фестиваль «{competition_title}» изменена после подачи. Заявитель: {applicant_name}. Изменено: {when}."),
            details_label="Что изменилось",
            details=details,
            button_label="Открыть заявку",
            button_url=link,
        )

        for address in emails:
            message = EmailMultiAlternatives(
                subject=f"{_REVISED_SUBJECT} — №{number}",
                body=body,
                from_email=self._from_email,
                to=[address],
            )
            message.attach_alternative(html_body, "text/html")
            send_bulk(message)
