"""RFC 9457 Problem Details rendering for the Competitions REST API v1.

Every non-2xx response the Competitions edge returns is an
``application/problem+json`` document (API-000 §8). This module is the single
place that maps the bounded context's error vocabulary — the application layer's
:class:`~apps.competitions.application.exceptions.ApplicationError` subclasses
(each carrying a stable :attr:`code`) and the domain's typed
:class:`~apps.competitions.domain.exceptions.CompetitionDomainError` hierarchy —
onto that wire format, so views never hand-assemble a problem body.

The generic RFC 9457 plumbing (``problem_response``, ``request_id``,
``validation_problem``) is shared with the Identity edge and reused verbatim.
"""

from __future__ import annotations

import re
from typing import Final

from rest_framework.request import Request
from rest_framework.response import Response

from apps.competitions.application.exceptions import ApplicationError
from apps.competitions.domain.exceptions import (
    CompetitionDomainError,
    CompetitionStateError,
    ConfigurationConflictError,
    ConfigurationInUseError,
    ConfigurationReferenceError,
    PublicationRequirementsNotMetError,
    ValueObjectValidationError,
)

# Reuse the platform's single RFC 9457 renderer (API-000 §8.1).
from apps.identity.presentation.api.v1.problems import (
    problem_response,
    request_id,
    validation_problem,
)

__all__ = ["competition_problem", "problem_response", "request_id", "user_facing_detail", "validation_problem"]

#: Application-error ``code`` → ``(status, type-suffix, title)``.
_APPLICATION_PROBLEM_MAP: Final[dict[str, tuple[int, str, str]]] = {
    "competition_not_found": (404, "not-found", "Resource not found"),
    "application_error": (400, "bad-request", "Bad request"),
}

_APPLICATION_FALLBACK: Final[tuple[int, str, str]] = (400, "bad-request", "Bad request")

#: What the organizer reads when the raw message is not addressed to them.
#:
#: ``title`` stays English and stable per ``type`` (API-000 §8.4); ``detail`` is what
#: is actually shown in the settings UI, so it is always Russian. A domain invariant
#: written for a developer is replaced by the sentence its category deserves.
_RU_APPLICATION_DETAIL: Final[dict[str, str]] = {
    "competition_not_found": "Фестиваль не найден.",
    "application_error": "Не удалось выполнить действие. Попробуйте ещё раз.",
}

_RU_FALLBACK: Final[str] = "Не удалось сохранить настройки фестиваля. Попробуйте ещё раз."

_CYRILLIC: Final = re.compile("[А-Яа-яЁё]")


def _ru_domain_detail(exc: CompetitionDomainError) -> str:
    """The Russian sentence a domain error's category deserves."""
    if isinstance(exc, PublicationRequirementsNotMetError):
        return "Фестиваль нельзя опубликовать: настройки заполнены не полностью."
    if isinstance(exc, CompetitionStateError):
        return "Действие недоступно на текущем этапе фестиваля — обновите страницу."
    if isinstance(exc, ConfigurationReferenceError):
        return "Этой записи в настройках уже нет — обновите страницу."
    if isinstance(exc, ConfigurationConflictError | ConfigurationInUseError):
        return "Такая запись уже есть или используется в других настройках."
    if isinstance(exc, ValueObjectValidationError):
        return "Проверьте заполненные поля: данные не подходят."
    return _RU_FALLBACK


def user_facing_detail(exc: ApplicationError | CompetitionDomainError) -> str:
    """The ``detail`` to show, guaranteed Russian.

    A message already written in Russian is deliberate wording for the organizer and
    passes through untouched; anything else is internal prose and is replaced.
    """
    message = str(exc)
    if message and _CYRILLIC.search(message):
        return message
    if isinstance(exc, ApplicationError):
        return _RU_APPLICATION_DETAIL.get(exc.code, _RU_FALLBACK)
    return _ru_domain_detail(exc)


def _domain_rendering(exc: CompetitionDomainError) -> tuple[int, str, str]:
    """Map a domain error to ``(status, type-suffix, title)`` by its category.

    Ordered most-specific first. A missing nested element is a ``404``; a
    uniqueness/overlap conflict or in-use deletion guard is a ``409``; an illegal
    lifecycle transition (or publication attempted on an incomplete configuration)
    is a ``409``/``422`` respectively; malformed value-object input is ``422``.
    """
    if isinstance(exc, PublicationRequirementsNotMetError):
        return 422, "business-rule-violation", "Publication requirements not met"
    if isinstance(exc, CompetitionStateError):
        return 409, "conflict", "Conflict"
    if isinstance(exc, ConfigurationReferenceError):
        return 404, "not-found", "Resource not found"
    if isinstance(exc, ConfigurationConflictError | ConfigurationInUseError):
        return 409, "conflict", "Conflict"
    if isinstance(exc, ValueObjectValidationError):
        return 422, "validation-error", "Validation failed"
    return 422, "business-rule-violation", "Business rule violation"


def competition_problem(
    exc: ApplicationError | CompetitionDomainError,
    *,
    instance: str,
    request: Request,
) -> Response:
    """Render an application or domain error as a Problem Details response."""
    if isinstance(exc, ApplicationError):
        status, type_suffix, title = _APPLICATION_PROBLEM_MAP.get(exc.code, _APPLICATION_FALLBACK)
    else:
        status, type_suffix, title = _domain_rendering(exc)
    return problem_response(
        status=status,
        type_suffix=type_suffix,
        title=title,
        detail=user_facing_detail(exc),
        instance=instance,
        correlation_id=request_id(request),
    )
