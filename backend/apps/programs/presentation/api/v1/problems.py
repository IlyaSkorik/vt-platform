"""RFC 9457 Problem Details rendering for the Programs REST API v1.

Maps this context's error vocabulary (every
:class:`~apps.programs.domain.exceptions.ProgramError` carries a stable ``code``)
onto ``application/problem+json`` (API-000 §8), so views never hand-assemble a
problem body from ad-hoc strings.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.programs.domain.exceptions import ProgramError

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "envelope",
    "problem_response",
    "program_problem",
    "request_id",
    "validation_problem",
]

PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"
PROBLEM_CONTENT_TYPE: Final = "application/problem+json"
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps a program error ``code`` to ``(status, type-suffix, title)``.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str]]] = {
    "program_not_found": (404, "not-found", "Resource not found"),
    "program_item_not_found": (404, "not-found", "Resource not found"),
    "program_share_not_found": (404, "not-found", "Resource not found"),
    "invalid_program_data": (400, "bad-request", "Bad request"),
    "item_not_in_program": (422, "unprocessable-entity", "Those items are not part of this program"),
    "performance_already_in_program": (409, "conflict", "This act already has a slot in the program"),
    "performance_not_available": (422, "unprocessable-entity", "This act cannot be scheduled"),
    "reorder_mismatch": (422, "unprocessable-entity", "A reorder must list every item exactly once"),
    "slug_unavailable": (503, "service-unavailable", "Could not mint a public link"),
}

_FALLBACK: Final[tuple[int, str, str]] = (400, "bad-request", "Bad request")


def request_id(request: Any) -> str:
    """Return the request's correlation id, minting one if the client sent none."""
    supplied = request.headers.get(_REQUEST_ID_HEADER)
    if supplied:
        return str(supplied)
    return str(uuid.uuid4())


def envelope(request: Any, data: Any, *, meta: dict[str, Any] | None = None, status: int = 200) -> Response:
    """Wrap ``data`` in the platform's ``{data, meta}`` envelope."""
    rid = request_id(request)
    payload_meta: dict[str, Any] = {"requestId": rid}
    if meta:
        payload_meta.update(meta)
    return Response({"data": data, "meta": payload_meta}, status=status, headers={_REQUEST_ID_HEADER: rid})


def problem_response(
    *,
    status: int,
    type_suffix: str,
    title: str,
    detail: str,
    instance: str,
    correlation_id: str,
    errors: list[dict[str, str]] | None = None,
) -> Response:
    """Build an ``application/problem+json`` :class:`Response` (RFC 9457)."""
    body: dict[str, Any] = {
        "type": f"{PROBLEM_BASE}{type_suffix}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
        "requestId": correlation_id,
    }
    if errors is not None:
        body["errors"] = errors
    return Response(body, status=status, content_type=PROBLEM_CONTENT_TYPE, headers={_REQUEST_ID_HEADER: correlation_id})


def program_problem(exc: ProgramError, *, instance: str, request: Any) -> Response:
    """Render a :class:`ProgramError` as a Problem Details response."""
    status, type_suffix, title = _PROBLEM_MAP.get(exc.code, _FALLBACK)
    return problem_response(
        status=status,
        type_suffix=type_suffix,
        title=title,
        detail=str(exc) or title,
        instance=instance,
        correlation_id=request_id(request),
    )


def validation_problem(serializer_errors: dict[str, Any], *, instance: str, request: Any) -> Response:
    """Render DRF serializer errors as a ``400`` validation Problem Details doc."""
    errors: list[dict[str, str]] = []
    for field, messages in serializer_errors.items():
        pointer = "/" if field == "non_field_errors" else f"/{field}"
        for message in messages if isinstance(messages, list) else [messages]:
            errors.append({"pointer": pointer, "code": "invalid", "detail": str(message)})
    return problem_response(
        status=400,
        type_suffix="validation-error",
        title="Validation failed",
        detail="One or more fields are invalid.",
        instance=instance,
        correlation_id=request_id(request),
        errors=errors,
    )
