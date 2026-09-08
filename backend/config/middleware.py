"""HTTP middleware for the VT Platform Django project."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpRequest, HttpResponse

from config.basic_auth import matches, presented_credentials


class AllowMediaFramingMiddleware:
    """Allow cross-origin iframes for uploaded media (PDF/image previews).

    The default :class:`~django.middleware.clickjacking.XFrameOptionsMiddleware`
    sets ``X-Frame-Options: DENY`` on every response, which blocks the staff SPA
    (different origin in local Docker) from embedding ``/media/**`` files.
    Media URLs are not HTML application pages — framing them for organizer
    previews is intentional.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        media_url = settings.MEDIA_URL if settings.MEDIA_URL.startswith("/") else f"/{settings.MEDIA_URL}"
        self._media_prefix = media_url if media_url.endswith("/") else f"{media_url}/"

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        path = request.path if request.path.startswith("/") else f"/{request.path}"
        if path.startswith(self._media_prefix):
            if "X-Frame-Options" in response:
                del response["X-Frame-Options"]
            # Prefer an explicit allow-list over removing framing protection entirely
            # when a frontend origin is known (CORS allowlist doubles as frame ancestors).
            origins = list(getattr(settings, "CORS_ALLOWED_ORIGINS", []) or [])
            if origins:
                response["Content-Security-Policy"] = f"frame-ancestors {' '.join(origins)}"
            else:
                response["Content-Security-Policy"] = "frame-ancestors *"
        return response


#: What the browser shows in its password prompt, and the key it caches the
#: credentials under. Stable on purpose — changing it re-prompts everybody.
_GATE_REALM = "VT Platform"


class SiteGateMiddleware:
    """Ask for a password before serving anything, on a deployment that is not public.

    The staging stand is a complete copy of the site — the same pages, the same
    admin, and whatever data has been loaded into it. It must not be reachable by
    a crawler or by anybody who guesses the subdomain, and ``X-Robots-Tag`` only
    asks politely.

    Configured by ``SITE_GATE_USER``/``SITE_GATE_PASSWORD``. **Unset means open**,
    which is the opposite default from the docs gate in :mod:`config.api_docs`,
    and deliberately so: there an unset variable would publish something that
    should never be public, whereas here it describes production, which *is* the
    public site. Unset also removes this middleware from the chain outright
    (``MiddlewareNotUsed``), so a deployment that does not use it pays nothing.

    Done here rather than in whatever proxy fronts the stack, because the
    exemption below is the interesting part and it belongs somewhere versioned
    and reviewed rather than in a text field in a proxy's web UI. It also
    survives replacing that proxy, and it keeps the stand closed even if someone
    reaches the container directly.
    """

    #: Answered before the gate. These two are what the container healthcheck and
    #: the deploy's own external check call, and both return a fixed literal
    #: without reading the request (``config/urls.py``) — there is no information
    #: behind them to protect. A gate that closed them would fail every rollout
    #: while protecting nothing.
    EXEMPT_PATHS = frozenset({"/healthz", "/readyz"})

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        user = getattr(settings, "SITE_GATE_USER", "") or ""
        password = getattr(settings, "SITE_GATE_PASSWORD", "") or ""
        if not user or not password:
            raise MiddlewareNotUsed
        self.get_response = get_response
        self._expected = (user, password)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path in self.EXEMPT_PATHS:
            return self.get_response(request)
        presented = presented_credentials(request)
        if presented is not None and matches(presented, self._expected):
            return self.get_response(request)
        # 401 rather than 404: unlike the docs gate, this hides nothing whose
        # existence is worth denying — the address is a stand somebody was given
        # on purpose, and a browser needs the challenge to offer its prompt.
        response = HttpResponse("Authorization required.", status=401, content_type="text/plain; charset=utf-8")
        response["WWW-Authenticate"] = f'Basic realm="{_GATE_REALM}"'
        return response
