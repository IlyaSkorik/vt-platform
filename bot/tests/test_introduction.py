"""The introduction is the one place where a question could be mistaken for an answer.

These are the cases that decide whether somebody's first message reaches a human at all.
"""

import pytest

from support_bot.handlers.private import looks_like_a_failed_phone


@pytest.mark.parametrize(
    "text",
    [
        "891612345",  # a digit short
        "+7 916 123 45",
        "7 (916) 123-45",
        "79161234567890123",  # far too long to be dialled
    ],
)
def test_a_mistyped_number_is_recognised_as_one(text: str) -> None:
    assert looks_like_a_failed_phone(text)


@pytest.mark.parametrize(
    "text",
    [
        # Eight digits in a sentence. Counting digits alone would answer this with
        # «это не похоже на номер» and never pass the question on.
        "не могу оплатить 1500 за конкурс 2026",
        "не грузится фото",
        "ошибка 500 при загрузке",
        # Too few digits to be a phone number at all: relayed as content rather than corrected.
        "8916",
        "",
    ],
)
def test_a_question_is_never_mistaken_for_a_number(text: str) -> None:
    assert not looks_like_a_failed_phone(text)
