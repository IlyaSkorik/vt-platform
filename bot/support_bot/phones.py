"""Phone numbers: one way in, one way out.

Stored in E.164 (`+79130000000`) because that is what survives being copied into a dialler, and
displayed grouped because that is what a person reads off a topic title without stopping to count
digits.
"""

import re

RUSSIAN_LENGTH = 11
MIN_DIGITS = 11
MAX_DIGITS = 15


def normalise_phone(raw: str) -> str | None:
    """`8 (913) 000-00-00` → `+79130000000`, or None when it is not a phone number at all."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == RUSSIAN_LENGTH and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == RUSSIAN_LENGTH - 1:
        # Ten digits is a Russian number typed without the country code — the common case
        # whenever someone types instead of tapping the button.
        digits = "7" + digits
    if not MIN_DIGITS <= len(digits) <= MAX_DIGITS:
        return None
    return "+" + digits


def format_phone(phone: str) -> str:
    """`+79130000000` → `+7 913 000-00-00`. Anything that is not a Russian number is left alone."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) != RUSSIAN_LENGTH or not digits.startswith("7"):
        return phone
    return f"+{digits[0]} {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:]}"
