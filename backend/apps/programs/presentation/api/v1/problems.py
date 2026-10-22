"""RFC 9457 Problem Details rendering for the Programs REST API v1.

Maps this context's error vocabulary (every
:class:`~apps.programs.domain.exceptions.ProgramError` carries a stable ``code``)
onto ``application/problem+json`` (API-000 §8), so views never hand-assemble a
problem body from ad-hoc strings.
"""

from __future__ import annotations

import re
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
    "user_facing_detail",
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
    "program_column_not_found": (404, "not-found", "Resource not found"),
    # A link that was not granted control is refused exactly like one that does not
    # exist, so an audience link cannot be probed for whether it is the host's.
    "running_order_not_controllable": (404, "not-found", "Resource not found"),
    "invalid_program_data": (400, "bad-request", "Bad request"),
    "item_not_in_program": (422, "unprocessable-entity", "Those items are not part of this program"),
    "performance_already_in_program": (409, "conflict", "This act already has a slot in the program"),
    "performance_not_available": (422, "unprocessable-entity", "This act cannot be scheduled"),
    "program_conflict": (409, "conflict", "The program changed while you were editing it"),
    "program_numbers_frozen": (409, "conflict", "A published program cannot be regenerated"),
    # The restore point was consumed - most likely by another window, or by a reload
    # after the undo. A conflict rather than a 404: the program is there, its undo is not.
    "program_no_restore_point": (409, "conflict", "There is no rebuild left to undo"),
    "program_has_shares": (409, "conflict", "A published program cannot be deleted"),
    "reorder_mismatch": (422, "unprocessable-entity", "A reorder must list every item exactly once"),
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
    "program_not_found": "Программа не найдена.",
    "program_item_not_found": "Строки программы больше нет — обновите страницу.",
    "program_share_not_found": "Публичная ссылка не найдена.",
    "program_column_not_found": "Колонка не найдена — обновите страницу.",
    "running_order_not_controllable": "Этой программой нельзя управлять со сцены.",
    "invalid_program_data": "Проверьте заполненные поля: данные не подходят.",
    "item_not_in_program": "Эти выступления не входят в программу — обновите страницу.",
    "performance_already_in_program": "Это выступление уже стоит в программе.",
    "performance_not_available": "Это выступление нельзя поставить в программу.",
    "program_conflict": "Программа изменилась в другом окне — обновите страницу, чтобы не потерять чужие правки.",
    "program_numbers_frozen": "Программа уже опубликована — номера закреплены, пересобрать её нельзя.",
    "program_no_restore_point": "Отменять нечего: программу не пересобирали, либо отмену уже применили. Обновите страницу.",
    "program_has_shares": "У программы есть публичные ссылки — сначала отзовите их, потом удаляйте.",
    "reorder_mismatch": "Порядок задан неверно: список должен содержать все строки ровно по одному разу.",
    "slug_unavailable": "Не удалось создать публичную ссылку. Попробуйте ещё раз.",
}

#: The last resort, when even the code is one this edge does not know.
_RU_FALLBACK: Final[str] = "Не удалось изменить программу. Попробуйте ещё раз."

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


def program_problem(exc: ProgramError, *, instance: str, request: Any) -> Response:
    """Render a :class:`ProgramError` as a Problem Details response."""
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
