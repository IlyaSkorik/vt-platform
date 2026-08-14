"""The public status page — one address that answers "работает ли сайт?".

Deliberately **not** part of the SPA. The outage this page exists for was a lossy
uplink that dropped large packets: small responses arrived, the 740 KB bundle did
not. A status screen rendered by that bundle would have been unreachable in
exactly the incident it is meant to report. So this is one server-rendered
document with its stylesheet inlined — no bundle, no fonts, no external request
of any kind — a few kilobytes that survive a link too degraded to carry the app.

For the same reason it refreshes through ``<meta http-equiv="refresh">`` rather
than JavaScript: a page that cannot fetch its own bundle cannot poll either.

**Public means public.** The page is unauthenticated and names no version, no
hostname, no container, no exception text — a failing component reports only
*that* it failed. What an operator loses in detail here they get from the logs;
what an attacker would gain from a public inventory of internals is permanent.
Free disk is a percentage rather than bytes for the same reason: the shape of the
signal without the size of the disk.

Two representations of one truth:

* ``GET /status``       — the page a person opens when the site feels broken.
* ``GET /status.json``  — the same checks for external monitoring.

Both answer **503** when a critical component is down, so an uptime monitor
watching either one alerts without having to parse anything. A degraded
component — background jobs behind, disk filling — stays **200**: the site works,
and paging someone at 3am because a queue is slow is how alerts get muted.
"""

from __future__ import annotations

import html
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone

__all__ = ["status_json", "status_page"]

Health = Literal["ok", "degraded", "down"]

#: How long the page waits for the message broker before calling it down. The
#: database and cache answer in single-digit milliseconds or not at all; the
#: broker is the one check that can sit there, so it is the one with a leash.
_BROKER_TIMEOUT_SECONDS: Final = 2.0

#: Free-space thresholds. The deploy runbook (OPS-001 §1) asks for ~15 GB free
#: because a print run spools the diploma archive to disk on its way to the
#: bucket; these percentages are that requirement expressed proportionally, so
#: the check keeps meaning the same thing on a bigger disk.
_DISK_WARN_PERCENT: Final = 15.0
_DISK_CRITICAL_PERCENT: Final = 5.0

#: Seconds between automatic reloads of the page.
_REFRESH_SECONDS: Final = 30


@dataclass(frozen=True, slots=True)
class Component:
    """One checked dependency, as both the page and the JSON report it."""

    key: str
    name: str
    #: Shown under the name — what a person loses when this component is down,
    #: in their terms rather than the system's.
    detail: str
    health: Health
    #: Round-trip in milliseconds, or ``None`` when the check never completed.
    latency_ms: float | None
    #: Whether this component being down means the site itself is down. A
    #: critical failure drives the 503; a degraded one never does.
    critical: bool


def _timed(check: Any) -> tuple[bool, float | None]:
    """Run ``check``, reporting whether it passed and how long it took.

    Every exception is swallowed on purpose. A health check exists to *report* a
    failure, and one that propagates the failure it was asked about takes the
    status page down with the thing it was watching — which is precisely when the
    page is being read. The exception's text is discarded rather than surfaced:
    this document is public (see the module docstring).
    """
    started = time.perf_counter()
    try:
        check()
    except Exception:  # Deliberately broad — see the docstring: reporting, not raising.
        return False, None
    return True, round((time.perf_counter() - started) * 1000, 1)


def _check_database() -> Component:
    def probe() -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

    ok, latency = _timed(probe)
    return Component(
        key="database",
        name="База данных",
        detail="Заявки, результаты, учётные записи",
        health="ok" if ok else "down",
        latency_ms=latency,
        critical=True,
    )


def _check_cache() -> Component:
    def probe() -> None:
        # A write-then-read rather than a bare PING: a Redis that accepts
        # connections but refuses writes (out of memory, replica promoted to
        # read-only) passes the ping and fails the application.
        cache.set("status:probe", "1", timeout=10)
        if cache.get("status:probe") != "1":
            raise RuntimeError("cache did not return what it stored")

    ok, latency = _timed(probe)
    return Component(
        key="cache",
        name="Кэш",
        detail="Скорость страниц и сессии",
        health="ok" if ok else "down",
        latency_ms=latency,
        critical=True,
    )


def _check_broker() -> Component:
    def probe() -> None:
        # Imported here, not at module scope: the status page must render even
        # if Celery's dependencies are unhappy, and an ImportError at import
        # time would take the whole URLconf with it.
        from kombu import Connection

        with Connection(settings.CELERY_BROKER_URL) as conn:
            conn.ensure_connection(max_retries=0, timeout=_BROKER_TIMEOUT_SECONDS)

    ok, latency = _timed(probe)
    return Component(
        key="broker",
        name="Фоновые задачи",
        detail="Письма, дипломы, отчёты",
        # Degraded rather than down: a queue nobody is draining delays a diploma,
        # it does not stop a visitor reading the catalogue or filing an entry.
        health="ok" if ok else "degraded",
        latency_ms=latency,
        critical=False,
    )


def _check_disk() -> Component:
    root = Path(settings.MEDIA_ROOT)
    if not root.exists():
        root = Path(settings.BASE_DIR)

    free_percent: float | None = None

    def probe() -> None:
        nonlocal free_percent
        usage = shutil.disk_usage(root)
        free_percent = usage.free / usage.total * 100

    # The duration is discarded: a `statvfs` call times the kernel, not the
    # dependency, so reporting it would put a meaningless number on the page.
    ok, _ = _timed(probe)

    if not ok or free_percent is None:
        health: Health = "degraded"
        detail = "Место для дипломов и документов"
    elif free_percent < _DISK_CRITICAL_PERCENT:
        health = "down"
        detail = f"Свободно менее {_DISK_CRITICAL_PERCENT:.0f}%"
    elif free_percent < _DISK_WARN_PERCENT:
        health = "degraded"
        detail = f"Свободно {free_percent:.0f}%"
    else:
        health = "ok"
        detail = f"Свободно {free_percent:.0f}%"

    return Component(
        key="disk",
        name="Дисковое пространство",
        detail=detail,
        health=health,
        # A disk with nothing left stops a print run and every upload, so at the
        # critical threshold this is as fatal as a database that will not answer.
        critical=health == "down",
        latency_ms=None,
    )


def _collect() -> list[Component]:
    return [_check_database(), _check_cache(), _check_broker(), _check_disk()]


def _overall(components: list[Component]) -> Health:
    if any(c.health == "down" and c.critical for c in components):
        return "down"
    if any(c.health != "ok" for c in components):
        return "degraded"
    return "ok"


# --- Presentation ---------------------------------------------------------
#
# The palette is the design system's, reached the same way
# ``apps/emailing/templates.py`` reaches it: semantic tokens resolved to HEX,
# because a standalone document has no stylesheet to import. Keep the two in step
# when the palette moves.

_FONT_STACK: Final = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif"

# Light theme — vt-light.css.
_INK: Final = "#141829"
_INK_BODY: Final = "#343a54"
_INK_MUTED: Final = "#656d90"
_PAGE: Final = "#f6f7fb"
_CARD: Final = "#ffffff"
_BORDER: Final = "#d7dbe9"
_BORDER_SOFT: Final = "#eceef6"

# Dark theme — vt-dark.css, resolved from oklch.
_D_INK: Final = "#f9fafb"
_D_INK_BODY: Final = "#caced1"
_D_INK_MUTED: Final = "#9a9fa3"
_D_PAGE: Final = "#020304"
_D_CARD: Final = "#0a1016"
_D_PANEL: Final = "#10181f"
_D_BORDER: Final = "#292f32"
_D_BORDER_SOFT: Final = "#171b1e"

#: Per health: the accent hue, its tinted surface, and the same pair for dark.
#: The hues are the status colours the transactional emails already use, so a
#: green pill means the same thing in an inbox and on this page.
_HUES: Final[dict[Health, tuple[str, str, str, str]]] = {
    "ok": ("#1f9d63", "#d6f5e4", "#47c86e", "#173829"),
    "degraded": ("#d98a0b", "#fdeecd", "#f6b900", "#3e3511"),
    "down": ("#d64545", "#fadcdc", "#ff4c4d", "#401d22"),
}

_VERDICT: Final[dict[Health, tuple[str, str]]] = {
    "ok": ("Все системы работают", "Сайт доступен, сбоев нет."),
    "degraded": (
        "Работает с ограничениями",
        "Сайт доступен, но часть служб отвечает не полностью.",
    ),
    "down": ("Сбой в работе", "Часть сайта сейчас недоступна. Мы уже занимаемся этим."),
}

_LABEL: Final[dict[Health, str]] = {
    "ok": "работает",
    "degraded": "частично",
    "down": "недоступно",
}


def _styles(accent: str, tint: str, d_accent: str, d_tint: str) -> str:
    """The whole stylesheet, inline. Light first, dark under the media query."""
    return (
        f"*{{box-sizing:border-box;}}"
        f"body{{margin:0;padding:32px 20px;background:{_PAGE};color:{_INK};"
        f"font-family:{_FONT_STACK};-webkit-font-smoothing:antialiased;}}"
        f".wrap{{max-width:620px;margin:0 auto;}}"
        f".card{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;overflow:hidden;"
        f"box-shadow:0 1px 2px rgba(20,24,41,.04),0 8px 24px rgba(20,24,41,.06);}}"
        f".rule{{height:4px;background:{accent};}}"
        f".head{{padding:28px 28px 24px;border-bottom:1px solid {_BORDER_SOFT};}}"
        f".pill{{display:inline-block;padding:5px 12px;border-radius:999px;background:{tint};"
        f"color:{_INK};font-size:13px;font-weight:600;letter-spacing:.01em;}}"
        f".title{{margin:14px 0 6px;font-size:26px;line-height:1.25;font-weight:700;letter-spacing:-.01em;}}"
        f".intro{{margin:0;color:{_INK_BODY};font-size:15px;line-height:1.55;}}"
        f".rows{{padding:8px 28px 4px;}}"
        f".row{{display:flex;align-items:center;gap:16px;padding:16px 0;"
        f"border-bottom:1px solid {_BORDER_SOFT};}}"
        f".row:last-child{{border-bottom:0;}}"
        f".dot{{flex:0 0 auto;width:10px;height:10px;border-radius:50%;}}"
        f".name{{flex:1 1 auto;min-width:0;}}"
        f".name b{{display:block;font-size:15px;font-weight:600;line-height:1.35;}}"
        f".name span{{display:block;margin-top:2px;color:{_INK_MUTED};font-size:13px;line-height:1.4;}}"
        f".state{{flex:0 0 auto;text-align:right;}}"
        f".state b{{display:block;font-size:14px;font-weight:600;line-height:1.35;}}"
        f".state span{{display:block;margin-top:2px;color:{_INK_MUTED};"
        f"font-size:12px;font-variant-numeric:tabular-nums;}}"
        f".foot{{padding:18px 28px;background:{_PAGE};border-top:1px solid {_BORDER_SOFT};"
        f"color:{_INK_MUTED};font-size:13px;line-height:1.5;}}"
        f".foot a{{color:inherit;}}"
        f".back{{display:block;margin:18px auto 0;text-align:center;color:{_INK_MUTED};"
        f"font-size:13px;text-decoration:none;}}"
        f".back:hover{{text-decoration:underline;}}"
        # Narrow screens: the latency column is the first thing to go, since the
        # word beside it already carries the verdict.
        f"@media (max-width:420px){{"
        f"body{{padding:20px 14px;}}.head,.rows,.foot{{padding-left:20px;padding-right:20px;}}"
        f".title{{font-size:22px;}}.state span{{display:none;}}}}"
        f"@media (prefers-color-scheme:dark){{"
        f"body{{background:{_D_PAGE};color:{_D_INK};}}"
        f".card{{background:{_D_CARD};border-color:{_D_BORDER};box-shadow:none;}}"
        f".rule{{background:{d_accent};}}"
        f".head{{border-color:{_D_BORDER_SOFT};}}"
        f".pill{{background:{d_tint};color:{_D_INK};}}"
        f".intro{{color:{_D_INK_BODY};}}"
        f".row{{border-color:{_D_BORDER_SOFT};}}"
        f".name span,.state span{{color:{_D_INK_MUTED};}}"
        f".foot{{background:{_D_PANEL};border-color:{_D_BORDER_SOFT};color:{_D_INK_MUTED};}}"
        f".back{{color:{_D_INK_MUTED};}}}}"
    )


def _render(components: list[Component], overall: Health, checked_at: str) -> str:
    accent, tint, d_accent, d_tint = _HUES[overall]
    title, intro = _VERDICT[overall]

    rows = []
    for component in components:
        hue = _HUES[component.health]
        latency = f"{component.latency_ms:.0f} мс" if component.latency_ms is not None else "&nbsp;"
        rows.append(
            f'<div class="row">'
            f'<i class="dot" style="background:{hue[0]}"></i>'
            f'<div class="name"><b>{html.escape(component.name)}</b>'
            f"<span>{html.escape(component.detail)}</span></div>"
            f'<div class="state"><b style="color:{hue[0]}">{_LABEL[component.health]}</b>'
            f"<span>{latency}</span></div>"
            f"</div>"
        )

    return (
        "<!DOCTYPE html>"
        '<html lang="ru">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        # A status page in a search result is a status page read at the wrong
        # moment: whatever it said when the crawler came is not what it says now.
        '<meta name="robots" content="noindex,nofollow">'
        f'<meta http-equiv="refresh" content="{_REFRESH_SECONDS}">'
        '<meta name="color-scheme" content="light dark">'
        f"<title>Статус сервиса — {html.escape(title)} — Взлёт талантов</title>"
        f"<style>{_styles(accent, tint, d_accent, d_tint)}</style>"
        "</head>"
        "<body>"
        '<div class="wrap"><div class="card">'
        '<div class="rule"></div>'
        f'<div class="head"><span class="pill">Статус сервиса</span>'
        f'<h1 class="title">{html.escape(title)}</h1>'
        f'<p class="intro">{html.escape(intro)}</p></div>'
        f'<div class="rows">{"".join(rows)}</div>'
        f'<div class="foot">Проверено {html.escape(checked_at)}. '
        f"Страница обновляется сама каждые {_REFRESH_SECONDS} секунд.</div>"
        "</div>"
        '<a class="back" href="/">← Вернуться на сайт</a>'
        "</div>"
        "</body></html>"
    )


def _no_store(response: HttpResponse) -> HttpResponse:
    """Never cached, anywhere.

    A cached status page is a page that reports the state of the site at some
    earlier moment — which, on the one occasion anybody reads it, is the one
    thing it must not do.
    """
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


def status_page(_request: HttpRequest) -> HttpResponse:
    """``GET /status`` — the human-readable status page."""
    components = _collect()
    overall = _overall(components)
    # The zone is named, not assumed. ``DJANGO_TIME_ZONE`` is UTC by default while
    # the people reading this page are three hours ahead of it, and a status page
    # that appears to be reporting three hours ago is worse than no page: the one
    # thing it has to convey is that the check just happened.
    checked_at = timezone.localtime().strftime("%d.%m.%Y в %H:%M %Z")

    return _no_store(
        HttpResponse(
            _render(components, overall, checked_at),
            content_type="text/html; charset=utf-8",
            status=503 if overall == "down" else 200,
        )
    )


def status_json(_request: HttpRequest) -> JsonResponse:
    """``GET /status.json`` — the same checks, for an uptime monitor."""
    components = _collect()
    overall = _overall(components)

    return _no_store(  # type: ignore[return-value]
        JsonResponse(
            {
                "status": overall,
                "checkedAt": timezone.localtime().isoformat(),
                "components": [
                    {
                        "key": c.key,
                        "name": c.name,
                        "status": c.health,
                        "latencyMs": c.latency_ms,
                        "critical": c.critical,
                    }
                    for c in components
                ],
            },
            status=503 if overall == "down" else 200,
        )
    )
