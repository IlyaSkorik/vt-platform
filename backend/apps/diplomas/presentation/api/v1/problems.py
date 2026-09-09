"""RFC 9457 Problem Details rendering for the Diplomas REST API v1.

Maps the domain's error vocabulary (each
:class:`~apps.diplomas.domain.exceptions.DiplomaError` carries a stable ``code``)
onto ``application/problem+json`` (API-000 §8), so views never hand-assemble a
problem body.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.diplomas.domain.exceptions import DiplomaError

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "diploma_problem",
    "envelope",
    "problem_response",
    "request_id",
    "user_facing_detail",
    "validation_problem",
]

PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"
PROBLEM_CONTENT_TYPE: Final = "application/problem+json"
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps a diploma error ``code`` to ``(status, type-suffix, title)``.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str]]] = {
    "template_not_found": (404, "not-found", "Resource not found"),
    "assignment_not_found": (404, "not-found", "Resource not found"),
    "assignment_conflict": (409, "conflict", "This nomination already has a template assigned"),
    "diploma_not_found": (404, "not-found", "Resource not found"),
    "submission_not_found": (404, "not-found", "Resource not found"),
    "diploma_conflict": (409, "conflict", "This performance already has a diploma"),
    "print_template_not_ready": (409, "conflict", "The template has no PDF to print over"),
    "print_job_not_found": (404, "not-found", "Resource not found"),
    "template_not_assigned": (409, "conflict", "This nomination has no template of that type"),
    "template_type_mismatch": (409, "conflict", "The template is of the wrong document type"),
    "field_type_not_allowed": (422, "unprocessable-entity", "This document type cannot carry that field"),
}

_FALLBACK: Final[tuple[int, str, str]] = (400, "bad-request", "Bad request")

#: What a person reads when the raw message is not addressed to them.
#:
#: ``title`` stays English and stable per ``type`` (API-000 §8.4 — clients key off
#: ``type``/``code``, never off text); ``detail`` is the field the UI actually shows,
#: so it is always Russian. Internal prose written for a developer is replaced here
#: rather than put in front of a user.
_RU_DETAIL: Final[dict[str, str]] = {
    "template_not_found": "Шаблон не найден.",
    "assignment_not_found": "Назначение шаблона не найдено.",
    "assignment_conflict": "У этой номинации уже назначен шаблон.",
    "diploma_not_found": "Документ не найден.",
    "submission_not_found": "Выступление не найдено.",
    "diploma_conflict": "По этому выступлению документ уже выпущен.",
    "print_template_not_ready": "У шаблона нет PDF-подложки для печати.",
    "print_job_not_found": "Задание на печать не найдено.",
    "template_not_assigned": "Для этой номинации не назначен шаблон такого типа.",
    "template_type_mismatch": "Шаблон другого типа документа.",
    "field_type_not_allowed": "Это поле нельзя разместить в документе такого типа.",
}

#: The last resort, when even the code is one this edge does not know.
_RU_FALLBACK: Final[str] = "Не удалось выполнить действие с документами. Попробуйте ещё раз."

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


def diploma_problem(exc: DiplomaError, *, instance: str, request: Any) -> Response:
    """Render a :class:`DiplomaError` as a Problem Details response."""
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
