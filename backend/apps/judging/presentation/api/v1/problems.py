"""RFC 9457 Problem Details rendering for the Judging REST API v1.

Maps this context's error vocabulary (every
:class:`~apps.judging.domain.exceptions.JudgingError` carries a stable ``code``) onto
``application/problem+json`` (API-000 §8), so views never hand-assemble a problem body
from ad-hoc strings.

Two of the mappings below are the ones that matter on a festival day, and they are
``409``s rather than ``403``s on purpose: a judge who gets "выступление закрыто" or "вы
не судите этот жанр" has not done anything forbidden, they are looking at a screen that
has moved on. A client should refresh, not apologise.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.judging.domain.exceptions import JudgingError

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "envelope",
    "judging_problem",
    "problem_response",
    "request_id",
    "user_facing_detail",
    "validation_problem",
]

PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"
PROBLEM_CONTENT_TYPE: Final = "application/problem+json"
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps a judging error ``code`` to ``(status, type-suffix, title)``.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str]]] = {
    "invalid_judging_data": (400, "bad-request", "Bad request"),
    "judging_setup_not_found": (404, "not-found", "Resource not found"),
    "jury_member_not_found": (404, "not-found", "Resource not found"),
    "scoring_not_found": (404, "not-found", "Resource not found"),
    "scorecard_not_found": (404, "not-found", "Resource not found"),
    "online_judging_disabled": (409, "conflict", "This festival does not judge online"),
    "performance_closed": (409, "conflict", "Scoring for this act is closed"),
    "not_assigned_to_genre": (409, "conflict", "This judge is not seated for this genre"),
    "unknown_criterion": (422, "unprocessable-entity", "A score was sent for an unknown criterion"),
}

_FALLBACK: Final[tuple[int, str, str]] = (400, "bad-request", "Bad request")

#: What a person reads when the raw message is not addressed to them.
#:
#: ``title`` stays English and stable per ``type`` (API-000 §8.4 — clients key off
#: ``type``/``code``, never off text); ``detail`` is the field the UI actually shows,
#: so it is always Russian.
_RU_DETAIL: Final[dict[str, str]] = {
    "invalid_judging_data": "Проверьте заполненные поля: данные не подходят.",
    "judging_setup_not_found": "Настройки судейства не найдены.",
    "jury_member_not_found": "Член жюри не найден.",
    "scoring_not_found": "Выступление не найдено или ещё не открыто для оценки.",
    "scorecard_not_found": "Оценка не найдена.",
    "online_judging_disabled": "Для этого фестиваля не включено онлайн-судейство.",
    "performance_closed": "Оценка этого выступления закрыта ведущим.",
    "not_assigned_to_genre": "Вы не судите этот жанр.",
    "unknown_criterion": "Оценка выставлена по критерию, которого нет в этом жанре.",
}

_RU_FALLBACK: Final[str] = "Не удалось выполнить действие. Попробуйте ещё раз."

_CYRILLIC: Final = re.compile("[А-Яа-яЁё]")


def user_facing_detail(message: str, *, code: str) -> str:
    """The ``detail`` to show, guaranteed Russian.

    A message already written in Russian is deliberate wording for the user and passes
    through untouched, specifics and all — "«Техника»: максимум 10 балла(ов)" is a far
    better sentence than any generic one this module could substitute.
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


def judging_problem(exc: JudgingError, *, instance: str, request: Any) -> Response:
    """Render a :class:`JudgingError` as a Problem Details response."""
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
