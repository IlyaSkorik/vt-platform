"""Unit tests for resolving a template field's printed text from a snapshot.

Pure — no Django, no database. Guards the regression where the layout
serializer's default ``config={"parts": [], "prefix": ""}`` made every field look
like a nomination block, so only the block rendered.
"""

from __future__ import annotations

from apps.diplomas.domain.value_objects import (
    AwardSnapshot,
    DiplomaSnapshot,
    NominationSnapshot,
    ParticipantSnapshot,
)
from apps.diplomas.infrastructure.pdf.field_values import field_text

# The empty default config the layout serializer stores on every field.
_DEFAULT_CONFIG = {"parts": [], "prefix": ""}


def _snapshot() -> DiplomaSnapshot:
    return DiplomaSnapshot(
        participant=ParticipantSnapshot(display_name="Иванов Иван", age=12),
        nomination=NominationSnapshot(title="Вокал", discipline="Эстрадный вокал"),
        award=AwardSnapshot(degree=None),
    )


def test_simple_field_renders_despite_default_empty_config() -> None:
    field = {
        "type": "participant_name",
        "binding": "participant.display_name",
        "config": _DEFAULT_CONFIG,
    }
    assert field_text(field, _snapshot(), number="000001") == "Иванов Иван"


def test_award_degree_is_skipped_when_absent() -> None:
    field = {"type": "award_degree", "binding": "award.degree", "config": _DEFAULT_CONFIG}
    assert field_text(field, _snapshot(), number="000001") is None


def test_nomination_block_joins_its_parts() -> None:
    field = {
        "type": "nomination_block",
        "binding": "nomination.block",
        "config": {"parts": ["title", "discipline"], "prefix": "Номинация:"},
    }
    assert field_text(field, _snapshot(), number="000001") == "Номинация: Вокал, Эстрадный вокал"


def test_qr_block_prints_the_number() -> None:
    field = {"type": "qr_block", "binding": "diploma.number", "config": _DEFAULT_CONFIG}
    assert field_text(field, _snapshot(), number="000123") == "000123"


def test_free_text_prints_its_own_value() -> None:
    field = {"type": "free_text", "binding": "", "value": "Поздравляем!", "config": _DEFAULT_CONFIG}
    assert field_text(field, _snapshot(), number="000001") == "Поздравляем!"
