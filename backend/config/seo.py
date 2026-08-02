"""``robots.txt`` and ``sitemap.xml`` — what a crawler reads before anything else.

These are site-wide facts rather than any one context's, so they live beside the
root URLconf instead of inside an app: ``robots.txt`` governs the whole address
space, and the sitemap's job is to describe the *site*, which happens to be
mostly competitions today.

The sitemap is generated, not a file in ``public/``. A static one would be a
promise about which competitions exist, kept only until the next one is
published; this reads the same public projection the catalog endpoint serves, so
it cannot list a competition a visitor would not be shown, or omit one they
would.
"""

from __future__ import annotations

from datetime import date, datetime
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from apps.competitions.composition import build_public_catalog_read_service

__all__ = ["robots_txt", "sitemap_xml"]

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
)

#: Static public pages, with how often they are worth re-reading and how much of
#: the site's weight each carries relative to the others.
_STATIC_PAGES: tuple[tuple[str, str, str], ...] = (
    ("/", "daily", "1.0"),
    ("/competitions", "daily", "0.9"),
    ("/privacy-policy", "yearly", "0.3"),
    ("/cookies", "yearly", "0.3"),
)


def _site_url() -> str:
    """The origin the public site is served from, without a trailing slash."""
    return str(settings.FRONTEND_BASE_URL).rstrip("/")


def robots_txt(_request: HttpRequest) -> HttpResponse:
    """``GET /robots.txt`` — what a crawler may fetch, and where the map is."""
    lines = ["User-agent: *"]
    lines.extend(f"Disallow: {path}" for path in _DISALLOWED)
    lines.append("")
    lines.append(f"Sitemap: {_site_url()}/sitemap.xml")
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
    base = _site_url()
    entries = [
        _url_entry(location=f"{base}{path}", lastmod=None, changefreq=changefreq, priority=priority)
        for path, changefreq, priority in _STATIC_PAGES
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
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    return HttpResponse(document, content_type="application/xml; charset=utf-8")
