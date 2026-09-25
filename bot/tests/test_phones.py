import pytest

from support_bot.phones import format_phone, normalise_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("8 (913) 000-00-00", "+79130000000"),
        ("+7 913 000 00 00", "+79130000000"),
        ("79130000000", "+79130000000"),
        # Ten digits: the way people type when they skip the country code.
        ("9130000000", "+79130000000"),
        ("+380 44 000 0000", "+380440000000"),
    ],
)
def test_normalises_the_shapes_people_actually_type(raw: str, expected: str) -> None:
    assert normalise_phone(raw) == expected


@pytest.mark.parametrize("raw", ["не знаю", "", "89", "8916", "1" * 16])
def test_rejects_what_cannot_be_dialled(raw: str) -> None:
    assert normalise_phone(raw) is None


def test_formats_russian_numbers_for_reading() -> None:
    assert format_phone("+79130000000") == "+7 913 000-00-00"


def test_leaves_foreign_numbers_alone() -> None:
    assert format_phone("+380440000000") == "+380440000000"
