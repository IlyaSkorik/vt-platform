"""RFC 9457 Problem Details rendering for the Participants REST API v1.

Every non-2xx response the Participants edge returns is an
``application/problem+json`` document (API-000 §8). This module is the single place
that maps the application layer's error vocabulary
(:class:`~apps.participants.application.exceptions.ApplicationError` subclasses,
each carrying a stable :attr:`code`) and DRF serializer validation errors onto that
wire format — so views never hand-assemble a problem body.

The mapping decouples HTTP from the use cases: a handler raises a typed application
error; here we translate its ``code`` into the right status, stable ``type`` URI,
human ``title``, and — where a DATA-002 business rule is violated — the rule id in
the ``code`` extension (API-001 §5).
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.participants.application.exceptions import ActivationBlockedError, ApplicationError

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "application_problem",
    "problem_response",
    "request_id",
    "user_facing_detail",
    "validation_problem",
]

#: Base URI for stable problem-type identifiers (API-000 §8.1). Clients key off the
#: ``type``/``code``, never the human-readable ``detail``.
PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"

PROBLEM_CONTENT_TYPE: Final = "application/problem+json"

#: Correlation-id request header echoed into every problem/response (API-000 §6.1).
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps an application error ``code`` to its HTTP rendering:
#: ``(status, type-suffix, title, business-code)``. ``business-code`` is the
#: DATA-002 rule id placed in the ``code`` extension, or ``None`` to omit it.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str, str | None]]] = {
    "participant_not_found": (404, "not-found", "Resource not found", None),
    "display_alias_already_in_use": (409, "conflict", "Display alias already in use", None),
    "invalid_input": (400, "validation-error", "Validation failed", None),
    "participant_state_conflict": (409, "conflict", "Conflict", None),
    "activation_blocked": (422, "business-rule-violation", "Activation blocked", "PRT-001"),
    "policy_violation": (422, "business-rule-violation", "Business rule violation", None),
}

#: Rendering for any application error whose ``code`` is not explicitly mapped.
_FALLBACK: Final[tuple[int, str, str, str | None]] = (400, "bad-request", "Bad request", None)

#: What a person reads when the raw message is not addressed to them.
#:
#: ``title`` stays English and stable per ``type`` (API-000 §8.4 — clients key off
#: ``type``/``code``, never off text); ``detail`` is the field the UI actually shows,
#: so it is always Russian. Internal prose written for a developer is replaced here
#: rather than put in front of a user.
_RU_DETAIL: Final[dict[str, str]] = {
    "participant_not_found": "Участник не найден.",
    "display_alias_already_in_use": "Такое отображаемое имя уже занято.",
    "invalid_input": "Проверьте заполненные поля: данные не подходят.",
    "participant_state_conflict": "Действие недоступно на текущем этапе — обновите страницу.",
    "activation_blocked": "Участника нельзя активировать: не выполнены условия.",
    "policy_violation": "Действие запрещено правилами платформы.",
}

#: The last resort, when even the code is one this edge does not know.
_RU_FALLBACK: Final[str] = "Не удалось выполнить действие. Попробуйте ещё раз."

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


def problem_response(
    *,
    status: int,
    type_suffix: str,
    title: str,
    detail: str,
    instance: str,
    correlation_id: str,
    code: str | None = None,
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
    if code is not None:
        body["code"] = code
    if errors is not None:
        body["errors"] = errors
    return Response(
        body,
        status=status,
        content_type=PROBLEM_CONTENT_TYPE,
        headers={_REQUEST_ID_HEADER: correlation_id},
    )


def application_problem(exc: ApplicationError, *, instance: str, request: Any) -> Response:
    """Render an :class:`ApplicationError` as a Problem Details response.

    An :class:`~apps.participants.application.exceptions.ActivationBlockedError`
    carries a machine-readable ``reason`` extension so the client can distinguish a
    missing responsible adult from missing consent (PRT-001).
    """
    status, type_suffix, title, code = _PROBLEM_MAP.get(exc.code, _FALLBACK)
    body_code = code
    if isinstance(exc, ActivationBlockedError):
        body_code = f"{code}:{exc.reason}" if code is not None else exc.reason
    return problem_response(
        status=status,
        type_suffix=type_suffix,
        title=title,
        detail=user_facing_detail(str(exc), code=exc.code),
        instance=instance,
        correlation_id=request_id(request),
        code=body_code,
    )


def validation_problem(serializer_errors: dict[str, Any], *, instance: str, request: Any) -> Response:
    """Render DRF serializer errors as a ``400`` validation Problem Details doc.

    Field-shape/type failures are ``400`` (API-000 §8.2); each entry carries a JSON
    Pointer to the offending field and the framework's validation message.
    """
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
