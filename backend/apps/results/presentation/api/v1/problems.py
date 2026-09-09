"""RFC 9457 Problem Details rendering for the Results REST API v1.

Maps this context's error vocabulary (every
:class:`~apps.results.domain.exceptions.ProtocolError` carries a stable ``code``) onto
``application/problem+json`` (API-000 §8), so views never hand-assemble a problem body
from ad-hoc strings.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.results.domain.exceptions import ProtocolError

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "envelope",
    "problem_response",
    "protocol_problem",
    "request_id",
    "user_facing_detail",
    "validation_problem",
]

PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"
PROBLEM_CONTENT_TYPE: Final = "application/problem+json"
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps a protocol error ``code`` to ``(status, type-suffix, title)``.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str]]] = {
    "protocol_not_found": (404, "not-found", "Resource not found"),
    "protocol_row_not_found": (404, "not-found", "Resource not found"),
    "invalid_protocol_data": (400, "bad-request", "Bad request"),
    "protocol_already_exists": (409, "conflict", "This nomination already has a protocol"),
    "performance_already_in_protocol": (409, "conflict", "This act already has a line in the protocol"),
    "performance_not_available": (422, "unprocessable-entity", "This act did not compete in this nomination"),
    "reorder_mismatch": (422, "unprocessable-entity", "A reorder must list every row exactly once"),
    "awards_incomplete": (422, "unprocessable-entity", "There are no results to publish"),
    "protocol_not_published": (409, "conflict", "These results are not published"),
    "slug_unavailable": (503, "service-unavailable", "Could not mint a public link"),
}

_FALLBACK: Final[tuple[int, str, str]] = (400, "bad-request", "Bad request")

#: What a person reads when the raw message is not addressed to them.
#:
#: ``title`` stays English and stable per ``type`` (API-000 §8.4 — clients key off
#: ``type``/``code``, never off text); ``detail`` is the field the UI actually shows,
#: so it is always Russian. Internal prose written for a developer is replaced here
#: rather than put in front of a user.
_RU_DETAIL: Final[dict[str, str]] = {
    "protocol_not_found": "Протокол не найден.",
    "protocol_row_not_found": "Строки протокола больше нет — обновите страницу.",
    "invalid_protocol_data": "Проверьте заполненные поля: данные не подходят.",
    "protocol_already_exists": "У этой номинации уже есть протокол.",
    "performance_already_in_protocol": "Это выступление уже есть в протоколе.",
    "performance_not_available": "Это выступление не участвовало в этой номинации.",
    "reorder_mismatch": "Порядок задан неверно: список должен содержать все строки ровно по одному разу.",
    "awards_incomplete": "Публиковать нечего: результаты не проставлены.",
    "protocol_not_published": "Результаты ещё не опубликованы.",
    "slug_unavailable": "Не удалось создать публичную ссылку. Попробуйте ещё раз.",
}

#: The last resort, when even the code is one this edge does not know.
_RU_FALLBACK: Final[str] = "Не удалось изменить протокол. Попробуйте ещё раз."

_CYRILLIC: Final = re.compile("[А-Яа-яЁё]")


def user_facing_detail(message: str, *, code: str) -> str:
    """The ``detail`` to show, guaranteed Russian.

    A message already written in Russian is deliberate wording for the user and passes
    through untouched, specifics and all; anything else is replaced by the sentence
    this error code deserves.
    """
    if message and _CYRILLIC.search(message):
        return message
    return _RU_DETAIL.get(code, _RU_FALLBACK)


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


def protocol_problem(exc: ProtocolError, *, instance: str, request: Any) -> Response:
    """Render a :class:`ProtocolError` as a Problem Details response."""
    status, type_suffix, title = _PROBLEM_MAP.get(exc.code, _FALLBACK)
    return problem_response(
        status=status,
        type_suffix=type_suffix,
        title=title,
        detail=user_facing_detail(str(exc), code=exc.code),
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
        detail="Проверьте заполненные поля.",
        instance=instance,
        correlation_id=request_id(request),
        errors=errors,
    )
