"""Every refusal a person can read is written in Russian.

Two guarantees are covered. First, each context's Problem Details edge replaces a
``detail`` that is not addressed to a person: the domain and application layers talk
to developers in English, and none of that prose may reach an applicant or an
organizer. Second, DRF's own refusals — throttling, a wrong method — go the same way.

The map of codes itself is checked too: a code added to a problem map without Russian
wording beside it would silently fall back to the generic sentence.
"""

from __future__ import annotations

import re

import pytest

_CYRILLIC = re.compile("[А-Яа-яЁё]")


def test_an_english_domain_message_never_reaches_the_applicant() -> None:
    from apps.applications.application.exceptions import SubmissionInvariantViolationError
    from apps.applications.presentation.api.v1.problems import user_facing_detail

    exc = SubmissionInvariantViolationError(
        "A submission must have a performance before it can be submitted.",
        domain_code="PerformanceRequiredError",
    )

    assert user_facing_detail(str(exc), code=exc.code) == "Выступление нельзя сохранить в таком виде — проверьте заполненные данные."


def test_a_russian_message_is_shown_as_written() -> None:
    """The specifics matter: whoever wrote Russian wrote it for the reader."""
    from apps.applications.presentation.api.v1.problems import user_facing_detail

    written = "Этот фестиваль требует указать педагога."

    assert user_facing_detail(written, code="submission_invariant_violation") == written


def test_an_unknown_code_still_gets_a_russian_sentence() -> None:
    from apps.applications.presentation.api.v1.problems import user_facing_detail

    assert _CYRILLIC.search(user_facing_detail("Something went wrong.", code="no_such_code"))


@pytest.mark.parametrize(
    "module",
    [
        "apps.applications.presentation.api.v1.problems",
        "apps.diplomas.presentation.api.v1.problems",
        "apps.identity.presentation.api.v1.problems",
        "apps.participants.presentation.api.v1.problems",
        "apps.programs.presentation.api.v1.problems",
        "apps.results.presentation.api.v1.problems",
        "apps.teachers.presentation.api.v1.problems",
    ],
)
def test_every_mapped_code_has_russian_wording(module: str) -> None:
    """A code rendered as a problem must have a sentence of its own."""
    import importlib

    problems = importlib.import_module(module)
    mapped = set(problems._PROBLEM_MAP)
    written = problems._RU_DETAIL

    assert mapped <= set(written), f"no Russian detail for: {sorted(mapped - set(written))}"
    assert all(_CYRILLIC.search(text) for text in written.values())


def test_the_competitions_edge_answers_the_organizer_in_russian() -> None:
    from apps.competitions.domain.exceptions import CompetitionStateError
    from apps.competitions.presentation.api.v1.problems import user_facing_detail

    exc = CompetitionStateError("The competition is published and locked.")

    assert user_facing_detail(exc) == "Действие недоступно на текущем этапе фестиваля — обновите страницу."


def test_drf_rewrites_its_half_translated_throttle_message() -> None:
    from rest_framework.exceptions import Throttled

    from config.api_errors import exception_handler

    response = exception_handler(Throttled(wait=5), {})

    assert response is not None
    assert response.data["detail"] == "Слишком много запросов. Повторите через 5 с."


def test_drf_refusals_with_english_prose_are_replaced() -> None:
    from rest_framework.exceptions import APIException

    from config.api_errors import exception_handler

    response = exception_handler(APIException("Something failed internally."), {})

    assert response is not None
    assert response.data["detail"] == "Не удалось выполнить действие. Попробуйте ещё раз."
