"""``robots.txt``, ``sitemap.xml`` and ``llms.txt`` — what a machine reads first.

These are site-wide facts rather than any one context's, so they live beside the
root URLconf instead of inside an app: ``robots.txt`` governs the whole address
space, and the sitemap's job is to describe the *site*, which happens to be
mostly competitions today.

The sitemap is generated, not a file in ``public/``. A static one would be a
promise about which competitions exist, kept only until the next one is
published; this reads the same public projection the catalog endpoint serves, so
it cannot list a competition a visitor would not be shown, or omit one they
would.

``llms.txt`` (llmstxt.org) is generated for the same reason and from the same
projection. It answers a different reader: a sitemap hands a crawler addresses to
fetch, while this hands a language model the facts it would otherwise guess at —
what the site is, which competitions exist right now, whether each is still
taking applications. The two documents disagreeing about which competitions exist
is the failure mode worth designing out, so they share a source rather than a
copy.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from apps.competitions.composition import build_public_catalog_read_service

if TYPE_CHECKING:
    from apps.competitions.application.read_models.public_catalog import PublicFestivalView

__all__ = ["SITE_NAME", "llms_txt", "robots_txt", "site_url", "sitemap_xml"]

#: The brand as it is written, wherever the server writes it. Lives here rather
#: than in ``spa.py`` because ``llms.txt`` needs it too, and the site announcing
#: itself under two spellings is precisely the confusion these documents exist to
#: prevent. Not a setting: it is the product's name, not the deployment's.
SITE_NAME = "Взлёт талантов"

#: Everything behind a sign-in, plus the public-but-not-indexable pages that
#: carry a child's name or a one-time token. This repeats what the ``noindex``
#: tags already say, deliberately: ``robots.txt`` stops the fetch, the tag stops
#: the indexing, and a crawler that honours only one of the two still behaves.
_DISALLOWED = (
    "/cabinet/",
    "/staff/",
    "/platform/",
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/verify-email",
    "/session-expired",
    "/unauthorized",
    "/staff-invitation/",
    # Personal data: the running order and the results protocol both name every
    # performing child, and a verification URL *is* an award's token.
    "/verify/",
    "/program/",
    "/protocol/",
    # Not a page — the API. Crawling it wastes budget on JSON no one searches for.
    "/api/",
    # The status page reports a moment, and a crawler can only ever record the
    # wrong one: indexed, it would answer "работает ли сайт?" with whatever was
    # true the last time a bot came by.
    "/status",
)

#: Static public pages, with how often they are worth re-reading and how much of
#: the site's weight each carries relative to the others.
_STATIC_PAGES: tuple[tuple[str, str, str], ...] = (
    ("/", "daily", "1.0"),
    ("/competitions", "daily", "0.9"),
    # The three legal documents, at the same weight: each is a page somebody
    # arrives at from a search or a pasted link before deciding whether to trust
    # the service with a child's data, and each changes about as often as the law
    # under it does.
    ("/terms", "yearly", "0.3"),
    ("/privacy-policy", "yearly", "0.3"),
    ("/cookies", "yearly", "0.3"),
)


def site_url() -> str:
    """The origin the public site is served from, without a trailing slash."""
    return str(settings.FRONTEND_BASE_URL).rstrip("/")


def robots_txt(_request: HttpRequest) -> HttpResponse:
    """``GET /robots.txt`` — what a crawler may fetch, and where the map is."""
    lines = ["User-agent: *"]
    lines.extend(f"Disallow: {path}" for path in _DISALLOWED)
    lines.append("")
    lines.append(f"Sitemap: {site_url()}/sitemap.xml")
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def _lastmod(value: datetime | date | None) -> str | None:
    """A ``<lastmod>`` date, or nothing when the projection has no timestamp.

    W3C date format, which is all a sitemap needs; omitted rather than faked with
    today's date, because a crawler that is told everything changed today learns
    nothing about what actually did.
    """
    if value is None:
        return None
    return (value.date() if isinstance(value, datetime) else value).isoformat()


def _url_entry(*, location: str, lastmod: str | None, changefreq: str, priority: str) -> str:
    parts = [f"    <loc>{escape(location)}</loc>"]
    if lastmod:
        parts.append(f"    <lastmod>{lastmod}</lastmod>")
    parts.append(f"    <changefreq>{changefreq}</changefreq>")
    parts.append(f"    <priority>{priority}</priority>")
    body = "\n".join(parts)
    return f"  <url>\n{body}\n  </url>"


def sitemap_xml(_request: HttpRequest) -> HttpResponse:
    """``GET /sitemap.xml`` — the public pages, with every visible competition."""
    base = site_url()
    entries = [
        _url_entry(location=f"{base}{path}", lastmod=None, changefreq=changefreq, priority=priority) for path, changefreq, priority in _STATIC_PAGES
    ]

    for festival in build_public_catalog_read_service().list_festivals():
        entries.append(
            _url_entry(
                location=f"{base}/competitions/{festival.slug or festival.id}",
                lastmod=_lastmod(festival.updated_at),
                # A competition's page changes while registration is open and
                # then settles; weekly is the honest middle rather than a claim
                # of daily churn that trains the crawler to ignore the field.
                changefreq="weekly",
                priority="0.8",
            )
        )

    document = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(entries) + "\n</urlset>\n"
    )
    return HttpResponse(document, content_type="application/xml; charset=utf-8")


# --- llms.txt -----------------------------------------------------------------
#
# Written in Russian, like the site. A model answering "какие конкурсы идут" will
# answer in the language of the question, and translating the catalog here would
# only introduce a second spelling of every competition's name.

#: What the site is, in the one paragraph a model will actually carry into an
#: answer. Kept to what is true of the platform rather than of any competition.
_LLMS_SUMMARY = (
    "Платформа для проведения детских творческих фестивалей и конкурсов: "
    "афиша мероприятий, онлайн-подача заявок, публикация результатов и выдача дипломов. "
    "Организаторы ведут конкурс целиком на платформе, участники подают заявки "
    "и получают дипломы в личном кабинете."
)

#: The paragraphs between the summary and the first section. This is where a
#: reader is told how much to trust the list below, which matters more here than
#: in a sitemap: a model will repeat what it reads, including the omissions.
_LLMS_NOTES: tuple[str, ...] = (
    "Язык сайта — русский. Список мероприятий ниже собирается при каждом запросе из того же "
    "источника, что и страницы каталога, поэтому в нём не может оказаться мероприятия, которого "
    "нет на сайте, и не может пропасть то, которое есть.",
    "Страниц с персональными данными детей здесь нет намеренно: программа выступлений "
    "(`/program/`), протокол результатов (`/protocol/`) и проверка диплома (`/verify/`) называют "
    "конкретного ребёнка. Они открываются по прямой ссылке для тех, кому её дали, но закрыты в "
    "`robots.txt` и не предназначены ни для индексации, ни для обучения. Личные кабинеты "
    "(`/cabinet/`, `/staff/`, `/platform/`) закрыты авторизацией.",
)

#: Static public pages, each with what it is *for*. The descriptions are the
#: whole value of the file — a bare list of links tells a model nothing the paths
#: did not already say.
_LLMS_PAGES: tuple[tuple[str, str, str], ...] = (
    ("/", "Главная", "Что такое платформа, активные мероприятия, ближайшие события и последние результаты."),
    (
        "/competitions",
        "Каталог мероприятий",
        "Все публично видимые фестивали и конкурсы: сроки, номинации, форматы участия, стоимость.",
    ),
    ("/terms", "Условия использования", "Договор, который принимает пользователь при регистрации."),
    ("/privacy-policy", "Политика конфиденциальности", "Какие персональные данные собираются, зачем и на каком основании."),
    ("/cookies", "Политика cookies", "Какие cookie ставит сайт и как от них отказаться."),
)

#: The public status projection, in the words the site itself uses on a card.
_LLMS_STATUS: dict[str, str] = {
    "REGISTRATION_OPEN": "регистрация открыта",
    "COMING_SOON": "регистрация скоро откроется",
    "REGISTRATION_CLOSED": "регистрация закрыта",
    "RUNNING": "идёт сейчас",
    "COMPLETED": "завершён",
}


def _inline(value: str) -> str:
    """Organizer-authored text, made safe to sit inside a Markdown link.

    A title is whatever somebody typed into a form, and two of those characters
    end a link label early — a competition called "Ритм[2026]" would otherwise
    produce a line that renders as broken punctuation and parses as a different
    address. Newlines collapse for the same reason: one list item, one line.
    """
    collapsed = re.sub(r"\s+", " ", value).strip()
    for character in ("\\", "[", "]"):
        collapsed = collapsed.replace(character, f"\\{character}")
    return collapsed


def _festival_facts(festival: PublicFestivalView) -> str:
    """The one-line description of a competition: status first, then when and where.

    Facts only, and only the ones present. The organizer's own description is left
    out deliberately — it is marketing prose of unbounded length, and what a model
    needs from this file is the dates it would otherwise invent.
    """
    facts = [_LLMS_STATUS.get(festival.status, festival.status.lower())]
    if festival.season:
        facts.append(f"сезон {festival.season}")
    if festival.city:
        facts.append(_inline(festival.city))

    start = _lastmod(festival.competition_start)
    end = _lastmod(festival.competition_end)
    if start and end and start != end:
        facts.append(f"конкурс {start} — {end}")
    elif start:
        facts.append(f"конкурс {start}")

    # The deadline the participant actually races, when there is one: the explicit
    # application cut-off outranks the registration window's end date.
    deadline = _lastmod(festival.application_deadline) or _lastmod(festival.registration_end)
    if deadline:
        facts.append(f"приём заявок до {deadline}")

    if festival.organizer.name:
        facts.append(f"организатор — {_inline(festival.organizer.name)}")
    return "; ".join(facts) + "."


def llms_txt(_request: HttpRequest) -> HttpResponse:
    """``GET /llms.txt`` — the site as facts, for a model rather than a crawler."""
    base = site_url()
    lines = [f"# {SITE_NAME}", "", f"> {_LLMS_SUMMARY}", ""]
    for note in _LLMS_NOTES:
        lines.extend([note, ""])

    lines.append("## Основные страницы")
    lines.append("")
    lines.extend(f"- [{title}]({base}{path}): {description}" for path, title, description in _LLMS_PAGES)
    lines.append("")

    lines.append("## Мероприятия")
    lines.append("")
    festivals = build_public_catalog_read_service().list_festivals()
    if festivals:
        lines.extend(
            f"- [{_inline(festival.title)}]({base}/competitions/{festival.slug or festival.id}): {_festival_facts(festival)}"
            for festival in festivals
        )
    else:
        # Said out loud rather than left as an empty heading: a reader that finds
        # nothing under it cannot tell "no competitions yet" from "the list failed
        # to load", and only one of those is worth repeating to a person.
        lines.append("Пока не опубликовано ни одного мероприятия.")
    lines.append("")

    # The literal heading from the llms.txt spec, which marks the section a reader
    # short on context may drop. These two are machine documents about the site
    # rather than pages of it, so they are exactly what should go first.
    lines.append("## Optional")
    lines.append("")
    lines.append(f"- [sitemap.xml]({base}/sitemap.xml): полный список публичных адресов с датами обновления.")
    lines.append(f"- [robots.txt]({base}/robots.txt): что закрыто от обхода.")

    # Markdown content under a `.txt` name: served as plain text so a browser shows
    # it instead of offering to download it, which is what `text/markdown` gets you.
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")
