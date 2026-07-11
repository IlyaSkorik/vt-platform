"""HTTP middleware for the VT Platform Django project."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse


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
