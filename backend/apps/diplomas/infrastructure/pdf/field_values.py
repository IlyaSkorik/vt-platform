"""Resolve a template field to its printed text from a diploma snapshot.

Mirrors the frontend ``resolveFieldDisplay`` but over the frozen
:class:`DiplomaSnapshot`: a data field yields its snapshot value or ``None`` (the
field is then not drawn — a diploma never shows a placeholder), the nomination
block joins its chosen parts, free text shows its own value. ``award.degree`` is
``None`` on a print copy, so a Степень field simply does not appear.
"""

from __future__ import annotations

from typing import Any

from apps.diplomas.domain.value_objects import DiplomaSnapshot

__all__ = ["field_text"]

# Nomination block parts in canonical order → snapshot.nomination attribute.
_NOMINATION_PARTS = (
    ("title", "title"),
    ("discipline", "discipline"),
    ("participant_group", "participant_group"),
    ("age_category", "age_category"),
)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _teacher_roster(snapshot: DiplomaSnapshot, *, roles: bool = True) -> str | None:
    """The teachers as printed.

    With ``roles`` (a diploma): ``"role: name1, name2"``, grouped by role, one role
    per line — a diploma credits a teacher in a stated capacity.

    Without (a thank-you letter): the names alone, comma-separated. The letter
    already says it is a thank-you, so "Педагог: ФИО" would only restate the label
    printed beside the field.
    """
    if not roles:
        names = [name for teacher in snapshot.teachers if (name := _clean(teacher.name)) is not None]
        return ", ".join(names) or None

    order: list[str] = []
    by_role: dict[str, list[str]] = {}
    for teacher in snapshot.teachers:
        name = _clean(teacher.name)
        if name is None:
            continue
        role = _clean(teacher.role) or ""
        if role not in by_role:
            by_role[role] = []
            order.append(role)
        by_role[role].append(name)
    if not order:
        return None
    lines = [f"{role}: {', '.join(by_role[role])}" if role else ", ".join(by_role[role]) for role in order]
    return "\n".join(lines)


def _nomination_block(config: dict[str, Any], snapshot: DiplomaSnapshot) -> str | None:
    chosen = set(config.get("parts") or [])
    values: list[str] = []
    for key, attr in _NOMINATION_PARTS:
        if key not in chosen:
            continue
        value = _clean(getattr(snapshot.nomination, attr))
        if value is not None:
            values.append(value)
    if not values:
        return None
    body = ", ".join(values)
    prefix = _clean(config.get("prefix"))
    return f"{prefix} {body}" if prefix else body


def _by_binding(binding: str, snapshot: DiplomaSnapshot, *, number: str, teacher_roles: bool) -> str | None:
    match binding:
        case "participant.display_name":
            return _clean(snapshot.participant.display_name)
        case "participant.age":
            age = snapshot.participant.age
            return str(age) if age is not None else None
        case "member.full_name":
            # Only an individual diploma has one. On the collective's own sheet the
            # snapshot carries no member, so the field is simply not drawn.
            return _clean(snapshot.member.full_name) if snapshot.member is not None else None
        case "teacher.display_name":
            return _teacher_roster(snapshot, roles=teacher_roles)
        case "organization.name":
            return _clean(snapshot.organization.name)
        case "nomination.title":
            return _clean(snapshot.nomination.title)
        case "nomination.discipline":
            return _clean(snapshot.nomination.discipline)
        case "nomination.participant_group":
            return _clean(snapshot.nomination.participant_group)
        case "nomination.age_category":
            return _clean(snapshot.nomination.age_category)
        case "performance.title":
            return _clean(snapshot.performance.title)
        case "competition.title":
            return _clean(snapshot.competition.title)
        case "competition.date":
            return _clean(snapshot.competition.date)
        case "competition.city":
            return _clean(snapshot.competition.city)
        case "award.degree":
            return _clean(snapshot.award.degree)
        case "diploma.number":
            return _clean(number)
        case _:
            return None


def field_text(field: dict[str, Any], snapshot: DiplomaSnapshot, *, number: str) -> str | None:
    """The text a field prints, or ``None`` when it must not be drawn.

    Keyed on the field *type*, not on the shape of ``config``: the layout
    serializer stores a default ``{"parts": [], "prefix": ""}`` on every field, so
    a simple field must not be mistaken for a nomination block.

    A teacher field prints roles unless its config says otherwise
    (``{"roles": false}``). Expressed on the field rather than as a renderer flag,
    because the caller that knows the document kind already prepares the layout —
    so the renderer stays free of document-kind branches.
    """
    field_type = field.get("type")
    config = field.get("config") or {}
    if field_type == "nomination_block":
        return _nomination_block(config, snapshot)
    if field_type == "qr_block":
        # The block's caption is the diploma number; the renderer draws it beside
        # the QR image and the authenticity text (see ``renderer._draw_qr_block``).
        return _clean(number)
    binding = field.get("binding") or ""
    if field_type == "free_text" or not binding:
        return _clean(field.get("value"))
    return _by_binding(binding, snapshot, number=number, teacher_roles=config.get("roles", True) is not False)
