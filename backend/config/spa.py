"""Serving the SPA's ``index.html`` with its ``<head>`` already filled in.

Google executes JavaScript, so the client-side meta layer is enough for search.
The crawlers that build link previews — Telegram, VK, WhatsApp, Facebook — do
not. They fetch the HTML once, read the ``og:*`` tags in it, and leave. Against a
plain SPA shell that means every festival ever shared previews as the same
generic card, which is most of what a competition link is *for*.

So this is not server-side rendering of the application: the body is still the
empty ``#root`` Vite emitted, and React still renders it. Only the head is
resolved on the server, from the same public projection the catalog endpoint
reads. That is a few hundred bytes of work per request instead of a Node
renderer in production, and it is the whole of what the preview crawlers need.

**Structured data is deliberately absent here.** JSON-LD is read by search
engines, which run our JavaScript, so the client already covers it — and
re-deriving the schema.org graphs in Python would mean two definitions of one
document, kept in step by hand. The meta tags are the opposite case: nothing but
the server can give them to a preview crawler, so they have to live here.

**Opt-in.** Nothing is served unless ``SPA_INDEX_PATH`` names a built
``index.html``. Unset — the default, and the case while Vite serves the SPA —
the view raises ``Http404`` and every address behaves as it did before.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse

from apps.competitions.composition import build_public_catalog_read_service

from .seo import site_url

__all__ = ["head_facts_for", "spa_index"]

_SITE_NAME = "Взлёт талантов"

_DEFAULT_DESCRIPTION = "Афиша детских творческих фестивалей и конкурсов: условия участия, номинации, сроки подачи заявок и результаты."

#: Prefixes whose pages must never be indexed — the same set ``robots.txt``
#: disallows and the route guards mark, restated here because a preview crawler
#: that ignored both would otherwise get a fully-formed card for a password-reset
#: screen or a child's results protocol.
_PRIVATE_PREFIXES = (
    "/cabinet",
    "/staff",
    "/platform",
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/verify-email",
    "/session-expired",
    "/unauthorized",
    "/staff-invitation",
    "/verify",
    "/program",
    "/protocol",
)


@dataclass(frozen=True, slots=True)
class HeadFacts:
    """What the server can say about a page before React has rendered anything."""

    title: str
    description: str = _DEFAULT_DESCRIPTION
    canonical_path: str | None = None
    image_path: str | None = None
    image_alt: str | None = None
    og_type: str = "website"
    noindex: bool = False
    #: Use ``title`` as the whole document title, without the site-name suffix.
    standalone_title: bool = False
    #: Whether ``image_path`` is uploaded media (served by this process) rather
    #: than an asset shipped with the frontend bundle. The two can sit on
    #: different hosts, and an ``og:image`` pointing at the wrong one renders as
    #: no image at all.
    image_is_media: bool = False

    @property
    def document_title(self) -> str:
        return self.title if self.standalone_title else f"{self.title} — {_SITE_NAME}"


def _truncate(text: str, limit: int = 300) -> str:
    stripped = " ".join(text.split())
    return stripped if len(stripped) <= limit else f"{stripped[: limit - 3].rstrip()}…"


def _festival_facts(segment: str) -> HeadFacts:
    """The head for one competition, or a closed one when it does not resolve.

    A miss is the ordinary case here, not an error: the SPA answers 200 to every
    address, so a typo'd or withdrawn festival still reaches this view. Naming it
    anyway would hand a crawler a preview for a page that shows "not found".
    """
    festival = build_public_catalog_read_service().get_festival(segment)
    if festival is None:
        return HeadFacts(title="Фестиваль не найден", noindex=True)

    own = (festival.description or "").strip()
    if own:
        description = _truncate(own)
    else:
        where = f" в городе {festival.city}" if festival.city else ""
        description = (
            f"«{festival.title}» — творческий фестиваль сезона {festival.season}{where}. "
            "Номинации, сроки регистрации, стоимость участия и подача заявки онлайн."
        )

    return HeadFacts(
        title=f"{festival.title} — {festival.season}",
        description=description,
        canonical_path=f"/competitions/{festival.slug or festival.id}",
        image_path=festival.cover_image,
        image_alt=f"Афиша фестиваля «{festival.title}»",
        image_is_media=True,
        og_type="article",
    )


def head_facts_for(path: str) -> HeadFacts:
    """Resolve the head for a request path.

    Mirrors what the corresponding page declares client-side. Where the two ever
    disagree the client wins a moment later, so the cost of a mismatch is a
    wrong *preview*, not a wrong page — which is exactly the thing this module
    exists to get right.
    """
    normalized = "/" + path.strip("/") if path.strip("/") else "/"

    if normalized == "/":
        return HeadFacts(
            title=f"{_SITE_NAME} — фестивали и конкурсы детского творчества",
            standalone_title=True,
            description=(
                "Афиша детских творческих фестивалей и конкурсов: условия участия, номинации, "
                "сроки подачи заявок и результаты. Подайте заявку онлайн на платформе "
                "«Взлёт талантов»."
            ),
            canonical_path="/",
            image_path="/home-hero-bg.png",
            image_alt="Юные участники творческого фестиваля на сцене",
        )

    if normalized == "/competitions":
        return HeadFacts(
            title="Фестивали и конкурсы детского творчества",
            description=(
                "Каталог открытых творческих фестивалей и конкурсов: номинации, возрастные "
                "категории, сроки регистрации и стоимость участия. Заявка подаётся онлайн."
            ),
            canonical_path="/competitions",
        )

    if normalized.startswith("/competitions/"):
        segment = normalized.removeprefix("/competitions/").split("/", 1)[0]
        return _festival_facts(segment)

    if normalized == "/privacy-policy":
        return HeadFacts(
            title="Политика обработки персональных данных",
            description="Какие персональные данные обрабатывает платформа и для каких целей.",
            canonical_path="/privacy-policy",
        )

    if normalized == "/cookies":
        return HeadFacts(
            title="Политика использования cookies",
            description="Какие cookies использует платформа и зачем.",
            canonical_path="/cookies",
        )

    if any(normalized == prefix or normalized.startswith(f"{prefix}/") for prefix in _PRIVATE_PREFIXES):
        return HeadFacts(title=_SITE_NAME, standalone_title=True, noindex=True)

    # An address the SPA will render as its 404 screen.
    return HeadFacts(title="Страница не найдена", noindex=True)


def _absolute(path: str | None, origin: str) -> str | None:
    """Make a stored path absolute; crawlers reject a relative ``og:image``.

    ``origin`` is where the *file* lives, which is not necessarily where the site
    does: a competition's poster is a ``/media/…`` path served by this process,
    while ``/home-hero-bg.png`` ships with the bundle. Callers pass whichever
    applies rather than this guessing from the shape of the path.
    """
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    return f"{origin.rstrip('/')}{path if path.startswith('/') else f'/{path}'}"


def _meta(attribute: str, key: str, content: str | None) -> str | None:
    """One tag, marked ``data-seo`` so the client owns it after hydration.

    The browser-side writer updates and removes only tags carrying that marker.
    Without it the client would append a second ``<title>``/``og:image`` beside
    the server's — and the browser honours the first, so the *stale* one would
    win on every client-side navigation.
    """
    if not content:
        return None
    return f'<meta {attribute}="{key}" content="{html.escape(content, quote=True)}" data-seo>'


def render_head(facts: HeadFacts, *, media_origin: str | None = None) -> str:
    """The tags to splice into ``<head>`` for ``facts``.

    ``media_origin`` is where uploaded files are served from — this process,
    normally, so the view passes the request's own origin. It falls back to the
    site's, which is right whenever the two share a host.
    """
    canonical = f"{site_url()}{facts.canonical_path}" if facts.canonical_path and not facts.noindex else None
    image = _absolute(facts.image_path, (media_origin or site_url()) if facts.image_is_media else site_url())
    title = facts.document_title

    tags = [
        _meta("name", "description", facts.description),
        _meta("name", "robots", "noindex, nofollow" if facts.noindex else None),
        _meta("property", "og:title", title),
        _meta("property", "og:description", facts.description),
        _meta("property", "og:type", facts.og_type),
        _meta("property", "og:url", canonical),
        _meta("property", "og:site_name", _SITE_NAME),
        _meta("property", "og:locale", "ru_RU"),
        _meta("property", "og:image", image),
        _meta("property", "og:image:alt", facts.image_alt if image else None),
        _meta("name", "twitter:card", "summary_large_image" if image else "summary"),
    ]
    if canonical:
        tags.append(f'<link rel="canonical" href="{html.escape(canonical, quote=True)}" data-seo>')
    return "\n    ".join(tag for tag in tags if tag)


_TITLE_PATTERN = re.compile(r"<title>.*?</title>", re.DOTALL | re.IGNORECASE)
_HEAD_CLOSE = re.compile(r"</head>", re.IGNORECASE)
#: Tags the template may already carry from a previous concern; dropped so the
#: page never ships two descriptions with the browser picking the older one.
_STALE_META = re.compile(r'\s*<meta\s+name="description"[^>]*>', re.IGNORECASE)


@lru_cache(maxsize=4)
def _template(path: str, mtime: float) -> str:
    """The built shell, cached until the file changes.

    ``mtime`` is part of the key rather than a check inside: it makes a rebuilt
    bundle invalidate the cache by itself, so a deploy that swaps ``index.html``
    under a running process does not keep serving the previous one.
    """
    del mtime
    return Path(path).read_text(encoding="utf-8")


def render_document(template: str, facts: HeadFacts, *, media_origin: str | None = None) -> str:
    """Splice ``facts`` into the shell, replacing what it already claimed."""
    document = _STALE_META.sub("", template)
    head = render_head(facts, media_origin=media_origin)
    title_tag = f"<title>{html.escape(facts.document_title)}</title>"
    document, replaced = _TITLE_PATTERN.subn(title_tag, document, count=1)
    if not replaced:
        head = f"{title_tag}\n    {head}"
    return _HEAD_CLOSE.sub(f"    {head}\n  </head>", document, count=1)


def spa_index(request: HttpRequest) -> HttpResponse:
    """Serve the SPA shell for a browser route, head first."""
    configured = str(getattr(settings, "SPA_INDEX_PATH", "") or "")
    index = Path(configured)
    if not configured or not index.is_file():
        # Not deployed as a served bundle: behave as though the route does not
        # exist, so an unknown address still reaches the ordinary 404.
        raise Http404("No SPA bundle is configured.")

    facts = head_facts_for(request.path)
    document = render_document(
        _template(str(index), index.stat().st_mtime),
        facts,
        # Uploaded posters are served by this process, so its own origin is the
        # one that resolves them — not necessarily the site's.
        media_origin=request.build_absolute_uri("/"),
    )
    response = HttpResponse(document, content_type="text/html; charset=utf-8")
    # The head varies per competition and changes when an organizer edits one;
    # short enough that a rename shows up in previews the same day, long enough
    # that a shared link does not re-read the projection for every crawler.
    response["Cache-Control"] = "public, max-age=300"
    return response
