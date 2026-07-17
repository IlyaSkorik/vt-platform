"""Reusable HTML templates for transactional emails."""

from __future__ import annotations

import html


def render_transactional_email_html(
    *,
    title: str,
    intro: str,
    details_label: str,
    details: str,
    button_label: str,
    button_url: str,
    brand_label: str = "Взлет талантов",
    footer_label: str = "С уважением, команда «Взлет талантов»",
) -> str:
    safe_title = html.escape(title)
    safe_intro = html.escape(intro)
    safe_details = html.escape(details).replace("\n", "<br/>")
    safe_button_label = html.escape(button_label)
    safe_button_url = html.escape(button_url, quote=True)
    safe_details_label = html.escape(details_label)
    safe_brand_label = html.escape(brand_label)
    safe_footer_label = html.escape(footer_label)
    return (
        "<div style=\"margin:0;padding:24px;background:#f3f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;\">"
        "<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:640px;margin:0 auto;\">"
        "<tr><td>"
        "<div style=\"background:#ffffff;border:1px solid #dbe4f0;border-radius:14px;overflow:hidden;\">"
        "<div style=\"padding:16px 20px;background:linear-gradient(135deg,#1d4ed8,#1e40af);color:#fff;\">"
        f"<p style=\"margin:0;font-size:12px;opacity:.9;letter-spacing:.3px;text-transform:uppercase;\">{safe_brand_label}</p>"
        f"<h2 style=\"margin:6px 0 0;font-size:20px;line-height:1.3;\">{safe_title}</h2>"
        "</div>"
        "<div style=\"padding:18px 20px;color:#0f172a;line-height:1.6;\">"
        f"<p style=\"margin:0 0 14px;font-size:14px;\">{safe_intro}</p>"
        "<div style=\"margin:0 0 16px;padding:12px 14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;\">"
        f"<p style=\"margin:0 0 6px;font-size:12px;color:#475569;font-weight:700;text-transform:uppercase;\">{safe_details_label}</p>"
        f"<p style=\"margin:0;font-size:14px;color:#0f172a;\">{safe_details}</p>"
        "</div>"
        f"<a href=\"{safe_button_url}\" "
        "style=\"display:inline-block;background:#1d4ed8;color:#ffffff;text-decoration:none;padding:10px 16px;border-radius:10px;"
        "font-weight:600;font-size:14px;\">"
        f"{safe_button_label}</a>"
        "<p style=\"margin:16px 0 0;font-size:12px;color:#64748b;\">"
        "Если кнопка не работает, скопируйте ссылку из письма и откройте ее в браузере.</p>"
        "</div>"
        "<div style=\"padding:12px 20px;border-top:1px solid #e2e8f0;background:#f8fafc;color:#64748b;font-size:12px;\">"
        f"{safe_footer_label}"
        "</div>"
        "</div>"
        "</td></tr></table>"
        "</div>"
    )
