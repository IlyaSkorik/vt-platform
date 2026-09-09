"""The last stop before a DRF-level error reaches a person.

Most refusals on this platform are rendered by a context's own
``problems.py`` — those are RFC 9457 documents whose ``detail`` is written for the
reader. What passes *this* way is what DRF itself raises before any of that runs:
throttling, an unsupported method, a malformed body, a permission class saying no.
DRF ships Russian for most of those, but not all of it (its throttle message is
half-translated), and a view is always free to raise ``APIException`` with English
prose.

So the handler keeps DRF's own body and only guarantees its language: Russian text
passes through untouched, anything else is replaced by the sentence the status
deserves. Field-level validation errors are left alone — they come from serializers
and are already localized per field.
"""

from __future__ import annotations

import math
import re
from typing import Any, Final

from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

__all__ = ["exception_handler"]

_CYRILLIC: Final = re.compile("[А-Яа-яЁё]")

#: What each status says when DRF's own wording is not addressed to a person.
_RU_BY_STATUS: Final[dict[int, str]] = {
    400: "Проверьте отправленные данные.",
    401: "Войдите в систему, чтобы продолжить.",
    403: "Нет прав на это действие.",
    404: "Не найдено — возможно, запись была удалена.",
    405: "Это действие здесь недоступно.",
    406: "Такой формат ответа не поддерживается.",
    409: "Данные изменились — обновите страницу и повторите.",
    413: "Файл слишком большой.",
    415: "Такой тип файла не принимается.",
    429: "Слишком много запросов. Подождите немного и повторите.",
}

_RU_FALLBACK: Final = "Не удалось выполнить действие. Попробуйте ещё раз."


def _russian(message: str, status: int) -> str:
    if message and _CYRILLIC.search(message):
        return message
    return _RU_BY_STATUS.get(status, _RU_FALLBACK)


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF's handler, with the top-level ``detail`` guaranteed Russian."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    body = response.data
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        # DRF's throttle message is half-translated ("Запрос был проигнорирован.
        # Expected available in 5 seconds."), and the Cyrillic in its first half would
        # otherwise wave the English half through. It is rewritten whole.
        if isinstance(exc, Throttled):
            wait = getattr(exc, "wait", None)
            seconds = math.ceil(wait) if wait else None
            body["detail"] = f"Слишком много запросов. Повторите через {seconds} с." if seconds else _RU_BY_STATUS[429]
        else:
            body["detail"] = _russian(str(body["detail"]), response.status_code)
    return response
