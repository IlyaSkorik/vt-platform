"""RFC 9457 Problem Details rendering for the Applications REST API v1.

Maps the application layer's error vocabulary (each
:class:`~apps.applications.application.exceptions.ApplicationError` carries a stable
:attr:`code`) and DRF serializer validation errors onto ``application/problem+json``
(API-000 §8), so views never hand-assemble a problem body.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from rest_framework.response import Response

from apps.applications.application.exceptions import ApplicationError

__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "application_problem",
    "problem_response",
    "request_id",
    "validation_problem",
]

PROBLEM_BASE: Final = "https://api.vzlyot-talantov.ru/problems/"
PROBLEM_CONTENT_TYPE: Final = "application/problem+json"
_REQUEST_ID_HEADER: Final = "X-Request-ID"

#: Maps an application error ``code`` to ``(status, type-suffix, title)``.
_PROBLEM_MAP: Final[dict[str, tuple[int, str, str]]] = {
    "application_not_found": (404, "not-found", "Resource not found"),
    "submission_not_found": (404, "not-found", "Resource not found"),
    "competition_not_found": (404, "not-found", "Resource not found"),
    "applicant_not_found": (404, "not-found", "Resource not found"),
    "educational_organization_not_found": (404, "not-found", "Resource not found"),
    "additional_service_not_found": (404, "not-found", "Resource not found"),
    "application_reference_not_found": (404, "not-found", "Resource not found"),
    "submission_child_not_found": (404, "not-found", "Resource not found"),
    "permission_denied": (403, "forbidden", "Forbidden"),
    "invalid_input": (400, "validation-error", "Validation failed"),
    "file_too_large": (413, "payload-too-large", "File too large"),
    "unsupported_file_type": (415, "unsupported-media-type", "Unsupported file type"),
    "competition_closed": (409, "conflict", "Competition is not accepting applications"),
    "multiple_performances_not_allowed": (409, "conflict", "Only one performance per application"),
    "additional_service_not_available": (409, "conflict", "Service not available for this format"),
    "deadline_passed": (409, "conflict", "Deadline has passed"),
    "payment_receipt_required": (409, "conflict", "Payment receipt is required"),
    "parent_guardian_required": (422, "business-rule-violation", "Parent or guardian is required"),
    "application_state_conflict": (409, "conflict", "Conflict"),
    "submission_state_conflict": (409, "conflict", "Conflict"),
    "application_conflict": (409, "conflict", "Conflict"),
    "duplicate_child": (409, "conflict", "Conflict"),
    "application_invariant_violation": (422, "business-rule-violation", "Business rule violation"),
    "submission_invariant_violation": (422, "business-rule-violation", "Business rule violation"),
    "competition_combination_not_found": (422, "business-rule-violation", "Unknown competition combination"),
}

_FALLBACK: Final[tuple[int, str, str]] = (400, "bad-request", "Bad request")


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


def application_problem(exc: ApplicationError, *, instance: str, request: Any) -> Response:
    """Render an :class:`ApplicationError` as a Problem Details response."""
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
