"""Reusable HTML templates for transactional emails.

The layout is the "status card": a coloured rule across the top of the card and a
pill in its header, both taking their hue from the message's status. Eight of the
platform's eleven transactional emails exist to report a state — submitted,
awaiting payment, cancelled, revised, results published — so the state is carried
by the layout rather than left for the recipient to read out of the prose.

Every colour below is a value from the design system's primitive palette
(``frontend/src/shared/theme/tokens/primitive.css``) reached through a semantic
token (``themes/vt-light.css``); the HEX is repeated here only because an email
has no stylesheet to reference. Keep the two in step when the palette moves.

Email constraints that shape the markup:

* Layout is tables, not flex/grid — Outlook's Word rendering engine understands
  neither, and it ignores ``border-radius`` (the corners simply square off).
* The mark ships as a PNG (``frontend/public/logo-email.png``, derived from
  ``logo.svg``): Gmail, Outlook and Mail.ru all strip inline SVG.
* Styles are inline, since ``<style>`` blocks are dropped by several clients.
"""

from __future__ import annotations

import html
from typing import Final, Literal

from django.conf import settings

EmailStatus = Literal["info", "success", "warning", "danger"]

#: Per-status colours: the solid rule/pill hue, and the tinted surface the pill
#: sits on. Text on that surface is ``--text-primary``, which clears AA on all four.
_STATUS_COLOURS: Final[dict[EmailStatus, tuple[str, str]]] = {
    "info": ("#2f74d0", "#d7e7fb"),  # --info / --info-surface
    "success": ("#1f9d63", "#d6f5e4"),  # --success / --success-surface
    "warning": ("#d98a0b", "#fdeecd"),  # --warning / --warning-surface
    "danger": ("#d64545", "#fadcdc"),  # --danger / --danger-surface
}

_INK: Final = "#141829"  # --text-primary
_INK_BODY: Final = "#343a54"  # --text-secondary
_INK_MUTED: Final = "#656d90"  # --text-muted
_BRAND: Final = "#0e327c"  # --interactive-primary
_PAGE: Final = "#f6f7fb"  # --background-secondary
_BORDER: Final = "#d7dbe9"  # --border-default
_BORDER_SOFT: Final = "#eceef6"  # --border-subtle

_FONT_STACK: Final = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif"

#: Served from the web client's public root, which is also where the links in
#: these emails point — one origin the recipient's client has to reach, not two.
_LOGO_PATH: Final = "/logo-email.png"


def render_transactional_email_html(
    *,
    title: str,
    intro: str,
    details_label: str,
    details: str,
    button_label: str,
    button_url: str,
    status: EmailStatus = "info",
    status_label: str | None = None,
    brand_label: str = "Взлёт талантов",
    footer_label: str = "С уважением, команда «Взлёт талантов»",
    logo_url: str | None = None,
) -> str:
    """Render one transactional email.

    ``status`` picks the accent carried by the top rule and the header pill;
    ``status_label`` is the pill's text, and omitting it drops the pill while
    keeping the rule. ``logo_url`` overrides the mark's absolute URL (tests).
    """
    accent, accent_surface = _STATUS_COLOURS[status]
    mark_url = logo_url if logo_url is not None else f"{settings.FRONTEND_BASE_URL}{_LOGO_PATH}"

    safe_title = html.escape(title)
    safe_intro = html.escape(intro)
    safe_details = html.escape(details).replace("\n", "<br/>")
    safe_details_label = html.escape(details_label)
    safe_button_label = html.escape(button_label)
    safe_button_url = html.escape(button_url, quote=True)
    safe_brand_label = html.escape(brand_label)
    safe_footer_label = html.escape(footer_label)
    safe_logo_url = html.escape(mark_url, quote=True)

    pill = (
        f'<td align="right" style="vertical-align:middle;">'
        f'<span style="display:inline-block;padding:5px 11px;border-radius:999px;background:{accent_surface};'
        f"color:{_INK};font-size:10px;letter-spacing:1px;text-transform:uppercase;font-weight:700;"
        f'white-space:nowrap;">{html.escape(status_label)}</span></td>'
        if status_label
        else ""
    )

    return (
        f'<div style="margin:0;padding:24px 16px;background:{_PAGE};font-family:{_FONT_STACK};">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" '
        'style="max-width:640px;margin:0 auto;"><tr><td>'
        f'<div style="background:#ffffff;border:1px solid {_BORDER};border-radius:14px;overflow:hidden;">'
        # The status rule. Zeroed font metrics keep clients from padding it out to a text line.
        f'<div style="height:4px;line-height:4px;font-size:0;background:{accent};">&nbsp;</div>'
        # Header: mark, wordmark, status pill.
        f'<div style="padding:16px 24px;border-bottom:1px solid {_BORDER_SOFT};">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr>'
        '<td width="32" style="width:32px;padding-right:10px;vertical-align:middle;">'
        f'<img src="{safe_logo_url}" width="32" height="32" alt="" '
        'style="display:block;width:32px;height:32px;border:0;outline:none;text-decoration:none;"/></td>'
        f'<td style="vertical-align:middle;font-size:11px;letter-spacing:1.6px;text-transform:uppercase;'
        f'color:{_INK_BODY};font-weight:700;">{safe_brand_label}</td>'
        f"{pill}"
        "</tr></table></div>"
        # Body.
        '<div style="padding:24px;">'
        f'<h1 style="margin:0 0 12px;font-size:21px;line-height:1.25;color:{_INK};font-weight:600;">{safe_title}</h1>'
        f'<p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:{_INK_BODY};">{safe_intro}</p>'
        f'<div style="margin:0 0 24px;padding:14px 16px;background:{_PAGE};border:1px solid {_BORDER};border-radius:10px;">'
        f'<p style="margin:0 0 6px;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;'
        f'color:{_INK_MUTED};font-weight:700;">{safe_details_label}</p>'
        f'<p style="margin:0;font-size:15px;line-height:1.6;color:{_INK};font-variant-numeric:tabular-nums;">{safe_details}</p>'
        "</div>"
        # The call to action, centred. `align` on the cell is what Outlook obeys.
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">'
        '<tr><td align="center" style="text-align:center;">'
        f'<a href="{safe_button_url}" style="display:inline-block;background:{_BRAND};color:#ffffff;'
        'text-decoration:none;padding:13px 28px;border-radius:8px;font-weight:600;font-size:15px;">'
        f"{safe_button_label}</a></td></tr></table>"
        f'<p style="margin:20px 0 0;font-size:12px;line-height:1.5;color:{_INK_MUTED};text-align:center;">'
        "Кнопка не открывается? Скопируйте ссылку:<br/>"
        f'<span style="color:{_BRAND};word-break:break-all;">{safe_button_url}</span></p>'
        "</div>"
        # Footer.
        f'<div style="padding:14px 24px;border-top:1px solid {_BORDER_SOFT};background:{_PAGE};'
        f'color:{_INK_MUTED};font-size:12px;line-height:1.5;">'
        f"{safe_footer_label}<br/>Письмо отправлено автоматически, отвечать на него не нужно."
        "</div>"
        "</div>"
        "</td></tr></table>"
        "</div>"
    )
