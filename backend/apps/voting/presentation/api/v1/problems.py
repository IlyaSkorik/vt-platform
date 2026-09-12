"""RFC 9457 Problem Details rendering for the Voting REST API v1.

Maps this context's error vocabulary (every
:class:`~apps.voting.domain.exceptions.BallotError` carries a stable ``code``)
onto ``application/problem+json`` (API-000 §8), so views never hand-assemble a
problem body from ad-hoc strings.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.voting.domain.exceptions import BallotError

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "ballot_problem",
    "envelope",
    "problem_response",
    "request_id",
]

PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"
PROBLEM_CONTENT_TYPE: Final = "application/problem+json"
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps a ballot error ``code`` to ``(status, type-suffix, title)``.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str]]] = {
    "ballot_not_found": (404, "not-found", "Resource not found"),
    "nominee_not_found": (404, "not-found", "Resource not found"),
    "invalid_ballot_data": (400, "bad-request", "Bad request"),
    "ballot_not_open": (422, "unprocessable-entity", "The ballot is not in a state that allows this"),
    "too_few_nominees": (422, "unprocessable-entity", "A vote needs something to choose between"),
    "voting_closed": (422, "unprocessable-entity", "Voting is not open"),
    "nominee_withdrawn": (422, "unprocessable-entity", "That nominee is no longer on the ballot"),
    "already_voted": (409, "conflict", "This voter has already voted"),
    "vote_limit_reached": (409, "conflict", "This voter has no votes left"),
    # 429, not 403: a soft brake is a "come back later", and the person behind the
    # shared address is almost always a real member of the audience.
    "too_many_votes_from_network": (429, "too-many-requests", "Too many votes from this network"),
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


def ballot_problem(error: BallotError, *, instance: str, request: Any) -> Response:
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
