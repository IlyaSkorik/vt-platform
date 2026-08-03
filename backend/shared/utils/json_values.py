"""Narrowing helpers for values read back out of a JSON column.

A JSON column is the one place where a Python annotation is a *claim* rather than a
guarantee: the row may have been written by an older revision of the mapper, by a
data migration, or by hand. So a value arrives as ``object`` and has to be narrowed
before use.

These replace the ``int(value)  # type: ignore[arg-type]`` idiom that had spread
through the mappers. That form was strictly worse than no annotation: it told the
checker to trust an ``object``, which silenced the genuine "this can raise" warning,
and the raise was then swallowed by a surrounding ``except`` — so a malformed value
became a silent default with nothing left to point at it.

Framework-free by design (shared-kernel rule: nothing here imports Django or a
bounded context).
"""

from __future__ import annotations

__all__ = ["as_int"]


def as_int(value: object, *, default: int = 0, minimum: int | None = None) -> int:
    """Read ``value`` as a whole number, falling back to ``default``.

    Accepts an ``int`` or a decimal string; anything else — ``None``, a float, a
    list, unparseable text — reads as ``default``. ``bool`` is refused even though
    it is an ``int`` subclass, because a stored ``true`` meant a flag, not the
    number 1, and silently reading it as 1 hides a mapper bug.

    ``minimum`` clamps the result, for the common case of a count or sort order
    that cannot be negative.
    """
    parsed = default
    if isinstance(value, bool):
        parsed = default
    elif isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            parsed = int(text)
        except ValueError:
            parsed = default
    if minimum is not None:
        return max(minimum, parsed)
    return parsed
