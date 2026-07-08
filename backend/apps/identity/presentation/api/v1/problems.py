"""RFC 9457 Problem Details rendering for the Identity REST API v1.

Every non-2xx response the Identity edge returns is an
``application/problem+json`` document (API-000 §8). This module is the single
place that maps the application layer's error vocabulary
(:class:`~apps.identity.application.exceptions.ApplicationError` subclasses, each
carrying a stable :attr:`code`) and DRF serializer validation errors onto that
wire format — so views never hand-assemble a problem body.

The mapping decouples HTTP from the use cases: a handler raises a typed
application error; here we translate its ``code`` into the right status, stable
``type`` URI, human ``title``, and — where a DATA-002 business rule is violated —
the rule id in the ``code`` extension (API-001 §5). Error ``detail`` text is taken
from the exception message and is never keyed off by clients.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.identity.application.exceptions import (
    ApplicationError,
    UserStateConflictError,
    WeakPasswordError,
)

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "application_problem",
    "problem_response",
    "request_id",
    "unauthorized_problem",
    "validation_problem",
]

#: Base URI for stable problem-type identifiers (API-000 §8.1). Clients key off
#: the ``type``/``code``, never the human-readable ``detail``.
PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"

PROBLEM_CONTENT_TYPE: Final = "application/problem+json"

#: Correlation-id request header echoed into every problem/response (API-000 §6.1).
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps an application error ``code`` to its HTTP rendering:
#: ``(status, type-suffix, title, business-code)``. ``business-code`` is the
#: DATA-002 rule id placed in the ``code`` extension, or ``None`` to omit it.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str, str | None]]] = {
    "invalid_credentials": (401, "authentication-failed", "Authentication failed", None),
    "invalid_token": (401, "authentication-failed", "Authentication failed", None),
    "account_inactive": (403, "account-suspended", "Account suspended", "IDN-009"),
    "email_already_in_use": (409, "conflict", "Email already in use", "IDN-003"),
    "phone_already_in_use": (409, "conflict", "Phone number already in use", None),
    "weak_password": (422, "validation-error", "Validation failed", None),
    "invalid_input": (400, "validation-error", "Validation failed", None),
    "invalid_verification_token": (422, "validation-error", "Invalid verification token", None),
    "user_not_found": (404, "not-found", "Resource not found", None),
    "user_state_conflict": (409, "conflict", "Conflict", None),
    "policy_violation": (422, "business-rule-violation", "Business rule violation", None),
}

#: Rendering for any application error whose ``code`` is not explicitly mapped.
_FALLBACK: Final[tuple[int, str, str, str | None]] = (400, "bad-request", "Bad request", None)

#: Domain-error names (carried on ``UserStateConflictError.domain_code``) that the
#: generic ``409 conflict`` under-describes and must render as a distinct problem.
#: An expired email-verification link is a ``410 Gone`` (API-001 §4.2).
_STATE_CONFLICT_OVERRIDES: Final[dict[str, tuple[int, str, str, str | None]]] = {
    "VerificationExpiredError": (
        410,
        "token-expired",
        "Verification token expired",
        "email-verification-expired",
    ),
}


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

    A :class:`~apps.identity.application.exceptions.WeakPasswordError` expands into
    a field-level ``errors`` array (one entry per policy violation) so the client
    can render a precise checklist (API-000 §8.2).
    """
    status, type_suffix, title, code = _PROBLEM_MAP.get(exc.code, _FALLBACK)
    # A user-state conflict is a 409 by default, but some domain states are more
    # specific (an expired verification link is a 410 Gone) — refine by domain_code.
    if isinstance(exc, UserStateConflictError):
        status, type_suffix, title, code = _STATE_CONFLICT_OVERRIDES.get(
            exc.domain_code, (status, type_suffix, title, code)
        )
    errors: list[dict[str, str]] | None = None
    if isinstance(exc, WeakPasswordError):
        errors = [
            {"pointer": "/password", "code": "weak-password", "detail": violation}
            for violation in exc.violations
        ]
    return problem_response(
        status=status,
        type_suffix=type_suffix,
        title=title,
        detail=str(exc) or title,
        instance=instance,
        correlation_id=request_id(request),
        code=code,
        errors=errors,
    )


def validation_problem(
    serializer_errors: dict[str, Any], *, instance: str, request: Any
) -> Response:
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
        detail="One or more fields are invalid.",
        instance=instance,
        correlation_id=request_id(request),
        errors=errors,
    )


def unauthorized_problem(*, instance: str, request: Any, detail: str) -> Response:
    """Render a generic ``401`` (missing/rejected credentials, API-001 §5)."""
    return problem_response(
        status=401,
        type_suffix="unauthorized",
        title="Authentication required",
        detail=detail,
        instance=instance,
        correlation_id=request_id(request),
    )
