"""Reusable HTML templates for transactional emails.

The layout is the "status card": a coloured rule across the top of the card and a
pill in its header, both taking their hue from the message's status. Eight of the
platform's eleven transactional emails exist to report a state — submitted,
awaiting payment, cancelled, revised, results published — so the state is carried
by the layout rather than left for the recipient to read out of the prose.

Every colour below is a value from the design system's palette
(``frontend/src/shared/theme/tokens/primitive.css`` and the two theme files)
reached through a semantic token; the HEX is repeated here only because an email
has no stylesheet to reference, and the dark values are the ``vt-dark.css``
oklch tokens resolved to sRGB. Keep the two in step when the palette moves.

Email constraints that shape the markup:

* Layout is tables, not flex/grid — Outlook's Word rendering engine understands
  neither, and it ignores ``border-radius`` (the corners simply square off).
* The mark ships as a PNG (``frontend/public/logo-email.png``, derived from
  ``logo.svg``): Gmail, Outlook and Mail.ru all strip inline SVG.
* The light theme lives in inline styles, because several clients drop
  ``<style>`` entirely; the dark theme lives in the one ``<style>`` block, and
  every rule in it needs ``!important`` to outrank those inline styles.
* Declaring ``color-scheme`` is what stops Apple Mail, iOS Mail and Outlook from
  inverting the light palette themselves — it tells them the message brings its
  own dark theme. Gmail's Android auto-inversion honours no such opt-out; there
  the light palette gets machine-inverted whatever we send.
"""

from __future__ import annotations

import html
from typing import Final, Literal

from django.conf import settings

EmailStatus = Literal["info", "success", "warning", "danger"]

#: Per status: the rule/accent hue and the tinted surface its pill sits on, in
#: the light theme and then the dark one. The dark surfaces are the theme's
#: ``color-mix(status 20%, transparent)`` flattened over the card, since an email
#: cannot rely on alpha compositing.
_STATUS_COLOURS: Final[dict[EmailStatus, tuple[str, str, str, str]]] = {
    "info": ("#2f74d0", "#d7e7fb", "#00c9f6", "#083947"),
    "success": ("#1f9d63", "#d6f5e4", "#47c86e", "#173829"),
    "warning": ("#d98a0b", "#fdeecd", "#f6b900", "#3e3511"),
    "danger": ("#d64545", "#fadcdc", "#ff4c4d", "#401d22"),
}

# Light theme — vt-light.css.
_INK: Final = "#141829"  # --text-primary
_INK_BODY: Final = "#343a54"  # --text-secondary
_INK_MUTED: Final = "#656d90"  # --text-muted
_BRAND: Final = "#0e327c"  # --interactive-primary
_ON_BRAND: Final = "#ffffff"  # --text-on-brand
_PAGE: Final = "#f6f7fb"  # --background-secondary
_CARD: Final = "#ffffff"  # --surface-primary
_BORDER: Final = "#d7dbe9"  # --border-default
_BORDER_SOFT: Final = "#eceef6"  # --border-subtle

# Dark theme — vt-dark.css, resolved from oklch. The surface ladder is one step
# wider than the light theme's: that theme separates card from page with a
# shadow, and an email has none, so the separation has to come from value.
_D_INK: Final = "#f9fafb"  # --text-primary
_D_INK_BODY: Final = "#caced1"  # --text-secondary
_D_INK_MUTED: Final = "#9a9fa3"  # --text-muted
_D_BRAND: Final = "#099ec7"  # --interactive-primary
_D_ON_BRAND: Final = "#020504"  # --text-on-brand
_D_PAGE: Final = "#020304"  # --background-primary
_D_CARD: Final = "#0a1016"  # --surface-secondary
_D_PANEL: Final = "#10181f"  # --surface-elevated
_D_FOOT: Final = "#05090d"  # --surface-primary
_D_BORDER: Final = "#292f32"  # --border-default
_D_BORDER_SOFT: Final = "#171b1e"  # --border-subtle

_FONT_STACK: Final = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif"

#: Served from the web client's public root, which is also where the links in
#: these emails point — one origin the recipient's client has to reach, not two.
_LOGO_PATH: Final = "/logo-email.png"
_LOGO_DARK_PATH: Final = "/logo-email-dark.png"


def _dark_rules(prefix: str, accent: str, pill_surface: str) -> str:
    """The dark palette as CSS, with every selector under ``prefix``.

    Emitted twice: once inside ``prefers-color-scheme``, and once under Outlook.com's
    ``[data-ogsc]``, which is that client's way of announcing its own dark mode
    instead of supporting the media query.
    """
    return (
        f"{prefix}.vt-page{{background:{_D_PAGE}!important;}}"
        f"{prefix}.vt-card{{background:{_D_CARD}!important;border-color:{_D_BORDER}!important;}}"
        f"{prefix}.vt-rule{{background:{accent}!important;}}"
        f"{prefix}.vt-head{{border-color:{_D_BORDER_SOFT}!important;}}"
        f"{prefix}.vt-brand{{color:{_D_INK_BODY}!important;}}"
        f"{prefix}.vt-pill{{background:{pill_surface}!important;color:{_D_INK}!important;}}"
        f"{prefix}.vt-title{{color:{_D_INK}!important;}}"
        f"{prefix}.vt-intro{{color:{_D_INK_BODY}!important;}}"
        f"{prefix}.vt-panel{{background:{_D_PANEL}!important;border-color:{_D_BORDER}!important;}}"
        f"{prefix}.vt-panel-label{{color:{_D_INK_MUTED}!important;}}"
        f"{prefix}.vt-panel-value{{color:{_D_INK}!important;}}"
        f"{prefix}.vt-btn{{background:{_D_BRAND}!important;color:{_D_ON_BRAND}!important;}}"
        f"{prefix}.vt-fallback{{color:{_D_INK_MUTED}!important;}}"
        f"{prefix}.vt-url{{color:{_D_BRAND}!important;}}"
        f"{prefix}.vt-foot{{background:{_D_FOOT}!important;border-color:{_D_BORDER_SOFT}!important;color:{_D_INK_MUTED}!important;}}"
        # The plated mark sits at 1.5:1 against the dark card, so the dark theme
        # swaps in the bare comet instead of dimming the plate.
        f"{prefix}.vt-mark-light{{display:none!important;}}"
        f"{prefix}.vt-mark-dark{{display:block!important;}}"
    )


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
    logo_dark_url: str | None = None,
) -> str:
    """Render one transactional email as a complete HTML document.

    ``status`` picks the accent carried by the top rule and the header pill;
    ``status_label`` is the pill's text, and omitting it drops the pill while
    keeping the rule. ``logo_url`` / ``logo_dark_url`` override the mark's
    absolute URLs (tests).
    """
    accent, accent_surface, accent_dark, accent_surface_dark = _STATUS_COLOURS[status]
    # Resolved one at a time, so overriding both marks needs no configured settings.
    mark_url = logo_url if logo_url is not None else f"{settings.FRONTEND_BASE_URL}{_LOGO_PATH}"
    mark_dark_url = logo_dark_url if logo_dark_url is not None else f"{settings.FRONTEND_BASE_URL}{_LOGO_DARK_PATH}"

    safe_title = html.escape(title)
    safe_intro = html.escape(intro)
    safe_details = html.escape(details).replace("\n", "<br/>")
    safe_details_label = html.escape(details_label)
    safe_button_label = html.escape(button_label)
    safe_button_url = html.escape(button_url, quote=True)
    safe_brand_label = html.escape(brand_label)
    safe_footer_label = html.escape(footer_label)
    safe_logo_url = html.escape(mark_url, quote=True)
    safe_logo_dark_url = html.escape(mark_dark_url, quote=True)

    dark_css = _dark_rules("", accent_dark, accent_surface_dark)
    style = (
        ":root{color-scheme:light dark;supported-color-schemes:light dark;}"
        f"@media (prefers-color-scheme:dark){{{dark_css}}}"
        f"{_dark_rules('[data-ogsc] ', accent_dark, accent_surface_dark)}"
    )

    pill = (
        '<td align="right" style="vertical-align:middle;">'
        f'<span class="vt-pill" style="display:inline-block;padding:5px 11px;border-radius:999px;background:{accent_surface};'
        f"color:{_INK};font-size:10px;letter-spacing:1px;text-transform:uppercase;font-weight:700;"
        f'white-space:nowrap;">{html.escape(status_label)}</span></td>'
        if status_label
        else ""
    )

    return (
        "<!DOCTYPE html>"
        '<html lang="ru"><head>'
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width,initial-scale=1"/>'
        '<meta name="color-scheme" content="light dark"/>'
        '<meta name="supported-color-schemes" content="light dark"/>'
        f"<title>{safe_title}</title>"
        f"<style>{style}</style>"
        "</head>"
        f'<body class="vt-page" style="margin:0;padding:24px 16px;background:{_PAGE};font-family:{_FONT_STACK};">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" '
        'style="max-width:640px;margin:0 auto;"><tr><td>'
        f'<div class="vt-card" style="background:{_CARD};border:1px solid {_BORDER};border-radius:14px;overflow:hidden;">'
        # The status rule. Zeroed font metrics keep clients from padding it out to a text line.
        f'<div class="vt-rule" style="height:4px;line-height:4px;font-size:0;background:{accent};">&nbsp;</div>'
        # Header: mark, wordmark, status pill.
        f'<div class="vt-head" style="padding:16px 24px;border-bottom:1px solid {_BORDER_SOFT};">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr>'
        '<td width="32" style="width:32px;padding-right:10px;vertical-align:middle;">'
        f'<img class="vt-mark-light" src="{safe_logo_url}" width="32" height="32" alt="" '
        'style="display:block;width:32px;height:32px;border:0;outline:none;text-decoration:none;"/>'
        # Hidden from Outlook's Word engine entirely: it has no dark mode to serve it,
        # and it has been known to paint `display:none` images anyway.
        "<!--[if !mso]><!-->"
        f'<img class="vt-mark-dark" src="{safe_logo_dark_url}" width="32" height="32" alt="" '
        'style="display:none;width:32px;height:32px;border:0;outline:none;text-decoration:none;"/>'
        "<!--<![endif]-->"
        "</td>"
        f'<td class="vt-brand" style="vertical-align:middle;font-size:11px;letter-spacing:1.6px;text-transform:uppercase;'
        f'color:{_INK_BODY};font-weight:700;">{safe_brand_label}</td>'
        f"{pill}"
        "</tr></table></div>"
        # Body.
        '<div style="padding:24px;">'
        f'<h1 class="vt-title" style="margin:0 0 12px;font-size:21px;line-height:1.25;color:{_INK};font-weight:600;">{safe_title}</h1>'
        f'<p class="vt-intro" style="margin:0 0 20px;font-size:15px;line-height:1.6;color:{_INK_BODY};">{safe_intro}</p>'
        f'<div class="vt-panel" style="margin:0 0 24px;padding:14px 16px;background:{_PAGE};border:1px solid {_BORDER};border-radius:10px;">'
        f'<p class="vt-panel-label" style="margin:0 0 6px;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;'
        f'color:{_INK_MUTED};font-weight:700;">{safe_details_label}</p>'
        f'<p class="vt-panel-value" style="margin:0;font-size:15px;line-height:1.6;color:{_INK};'
        f'font-variant-numeric:tabular-nums;">{safe_details}</p>'
        "</div>"
        # The call to action, centred. `align` on the cell is what Outlook obeys.
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">'
        '<tr><td align="center" style="text-align:center;">'
        f'<a class="vt-btn" href="{safe_button_url}" style="display:inline-block;background:{_BRAND};color:{_ON_BRAND};'
        'text-decoration:none;padding:13px 28px;border-radius:8px;font-weight:600;font-size:15px;">'
        f"{safe_button_label}</a></td></tr></table>"
        f'<p class="vt-fallback" style="margin:20px 0 0;font-size:12px;line-height:1.5;color:{_INK_MUTED};text-align:center;">'
        "Кнопка не открывается? Скопируйте ссылку:<br/>"
        f'<span class="vt-url" style="color:{_BRAND};word-break:break-all;">{safe_button_url}</span></p>'
        "</div>"
        # Footer.
        f'<div class="vt-foot" style="padding:14px 24px;border-top:1px solid {_BORDER_SOFT};background:{_PAGE};'
        f'color:{_INK_MUTED};font-size:12px;line-height:1.5;">'
        f"{safe_footer_label}<br/>Письмо отправлено автоматически, отвечать на него не нужно."
        "</div>"
        "</div>"
        "</td></tr></table>"
        "</body></html>"
    )
