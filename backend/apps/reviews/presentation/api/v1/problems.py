"""RFC 9457 Problem Details rendering for the Reviews REST API v1.

Maps this context's error vocabulary (every
:class:`~apps.reviews.domain.exceptions.ReviewError` carries a stable ``code``)
onto ``application/problem+json`` (API-000 §8), so views never hand-assemble a
problem body from ad-hoc strings.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.reviews.domain.exceptions import ReviewError

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "envelope",
    "problem_response",
    "request_id",
    "review_problem",
]

PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"
PROBLEM_CONTENT_TYPE: Final = "application/problem+json"
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps a review error ``code`` to ``(status, type-suffix, title)``.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str]]] = {
    "review_page_not_found": (404, "not-found", "Resource not found"),
    "review_not_found": (404, "not-found", "Resource not found"),
    "invalid_review_data": (400, "bad-request", "Bad request"),
    # 422 rather than 404: the link works and the page is real, it has simply
    # stopped collecting — and the person standing at the banner deserves to be
    # told which of the two it is.
    "review_page_closed": (422, "unprocessable-entity", "This page no longer collects reviews"),
    # 422 as well, not 403: nothing about the caller is wrong, the request is
    # missing the one thing that would make storing it lawful.
    "consent_required": (422, "unprocessable-entity", "Consent is required to store a review"),
    "slug_unavailable": (503, "service-unavailable", "Could not mint a public link"),
}

_FALLBACK: Final[tuple[int, str, str]] = (400, "bad-request", "Bad request")


def request_id(request: Any) -> str:
    """The correlation id for this request, minting one if the edge did not."""
    existing = request.META.get("HTTP_X_REQUEST_ID") if hasattr(request, "META") else None
    return str(existing) if existing else str(uuid.uuid4())


def envelope(data: Any, request: Any, *, status: int = 200) -> Response:
    """Wrap a payload in the platform's ``{data, meta}`` envelope (API-000 §7)."""
    correlation_id = request_id(request)
    return Response(
        {"data": data, "meta": {"requestId": correlation_id}},
        status=status,
        headers={_REQUEST_ID_HEADER: correlation_id},
    )


def problem_response(*, status: int, type_suffix: str, title: str, detail: str, instance: str, request: Any) -> Response:
    """Render an ``application/problem+json`` body (API-000 §8)."""
    correlation_id = request_id(request)
    return Response(
        {
            "type": f"{PROBLEM_BASE}{type_suffix}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": instance,
            "requestId": correlation_id,
        },
        status=status,
        content_type=PROBLEM_CONTENT_TYPE,
        headers={_REQUEST_ID_HEADER: correlation_id},
    )


def review_problem(error: ReviewError, *, instance: str, request: Any) -> Response:
    """Render a domain error as a problem document.

    ``title`` stays English and stable per ``type`` (API-000 §8.4 — clients key off
    ``type``/``code``, never off text); ``detail`` is the field the interface shows
    and is always the domain's own Russian message, because every message in this
    context was written for the person on the other end of it.
    """
    status, type_suffix, title = _PROBLEM_MAP.get(error.code, _FALLBACK)
    return problem_response(
        status=status,
        type_suffix=type_suffix,
        title=title,
        detail=str(error) or title,
        instance=instance,
        request=request,
    )
