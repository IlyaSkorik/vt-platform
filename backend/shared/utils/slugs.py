"""Turning a Russian title into an address a person can read back over the phone.

Two contexts need this now — an organization's address and a competition's — and
they must agree, because "Взлёт талантов" appearing as two different slugs in two
places is the kind of inconsistency nobody notices until a link is wrong.

Deliberately simple and lossy: transliteration here is for URLs, not for a
faithful romanization standard, and the caller can always supply an explicit slug
when the derived one is not the one they want.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

__all__ = ["slugify", "unique_slug"]

_TRANSLITERATION = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    # Belarusian letters the Russian table does not cover: the platform's
    # competitions are Belarusian, and "Беларусь" must not slug to "belarus" with
    # a hole where ў was.
    "і": "i",
    "ў": "u",
    "'": "",
}


def slugify(value: str, *, fallback: str, max_length: int = 100) -> str:
    """Derive a URL segment from ``value``, falling back when nothing survives.

    A title written entirely in characters the table cannot map — an emoji, a
    Chinese name — reduces to an empty string, and an empty URL segment would
    silently become the parent path. ``fallback`` is what that becomes instead.
    """
    lowered = value.strip().lower()
    latin = "".join(_TRANSLITERATION.get(char, char) for char in lowered)
    slug = re.sub(r"[^a-z0-9]+", "-", latin).strip("-")
    return slug[:max_length].strip("-") or fallback


def unique_slug(
    value: str,
    *,
    fallback: str,
    is_taken: Callable[[str], bool],
    max_length: int = 100,
) -> str:
    """``slugify``, then suffix ``-2``, ``-3``… until the address is free.

    Two competitions may legitimately share a title across seasons, so collisions
    are expected rather than exceptional. The first claimant keeps the clean
    address; later ones are numbered, which is the behaviour a reader expects
    from every other publishing tool.
    """
    base = slugify(value, fallback=fallback, max_length=max_length)
    if not is_taken(base):
        return base
    for suffix in _suffixes():
        # Trim the stem, not the suffix: a truncated "-12" is a different, and
        # possibly already taken, address.
        candidate = f"{base[: max_length - len(suffix) - 1].strip('-')}-{suffix}"
        if not is_taken(candidate):
            return candidate
    raise RuntimeError(f"Could not find a free slug for {value!r}.")


def _suffixes() -> Iterable[str]:
    """``2``, ``3``, … bounded so a broken ``is_taken`` cannot spin forever."""
    return (str(number) for number in range(2, 1000))
